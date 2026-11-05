/* Read-only bounded directory transport. Security gates deliberately fail closed.
 * Filesystem work lives only on the worker. No Ru VM or editor dependencies. */
#include "ru_directory_io.h"
#include <stddef.h>
#include <string.h>
typedef char DirEventSize[(sizeof(RuDirEvent)==8192)?1:-1];
typedef char DirDataOffset[(offsetof(RuDirEvent,data)==2160)?1:-1];
static uint16_t upper16(uint16_t c){return c>='a'&&c<='z'?(uint16_t)(c-32):c;}
static int component_ok(const uint16_t *s,uint32_t n){
    uint32_t i,base=0; uint16_t a,b,c,d;
    if(!n||n>255||s[n-1]=='.'||s[n-1]==' ')return 0;
    for(i=0;i<n;i++){
        uint16_t v=s[i];
        if(v<32||v==127||v=='/'||v=='\\'||v==':'||v=='<'||v=='>'||v=='"'||v=='|'||v=='?'||v=='*')return 0;
        if(v>=0xd800&&v<=0xdbff){if(i+1>=n||s[i+1]<0xdc00||s[i+1]>0xdfff)return 0;i++;}
        else if(v>=0xdc00&&v<=0xdfff)return 0;
    }
    while(base<n&&s[base]!='.')base++;
    a=upper16(s[0]);b=base>1?upper16(s[1]):0;c=base>2?upper16(s[2]):0;d=base>3?upper16(s[3]):0;
    if(base==3&&((a=='C'&&b=='O'&&c=='N')||(a=='P'&&b=='R'&&c=='N')||(a=='A'&&b=='U'&&c=='X')||(a=='N'&&b=='U'&&c=='L')))return 0;
    if(base==4&&((a=='C'&&b=='O'&&c=='M')||(a=='L'&&b=='P'&&c=='T'))&&((d>='1'&&d<='9')||d==0xb9||d==0xb2||d==0xb3))return 0;
    if((base==6&&a=='C'&&b=='O'&&c=='N'&&upper16(s[3])=='I'&&upper16(s[4])=='N'&&s[5]=='$')||
       (base==7&&a=='C'&&b=='O'&&c=='N'&&upper16(s[3])=='O'&&upper16(s[4])=='U'&&upper16(s[5])=='T'&&s[6]=='$'))return 0;
    return 1;
}
static int root_ok(const uint16_t *s,uint32_t n){
    uint32_t i,start,parts=0;
    if(!s||n<3||n>=RU_DIR_PATH_UNITS||upper16(s[0])<'A'||upper16(s[0])>'Z'||s[1]!=':'||s[2]!='\\')return 0;
    start=3;
    for(i=3;i<=n;i++)if(i==n||s[i]=='\\'){
        if(i==n&&i==start)return n==3; /* no trailing separator except drive root */
        if(!component_ok(s+start,i-start)||++parts>32)return 0;
        start=i+1;
    }
    return 1;
}
/* Validate a FILE_ID_BOTH_DIR_INFO record without trusting offset arithmetic.
 * The API supplies no used length. Zero-fill the buffer first; validate each
 * name and next offset against its full fixed allocation. */
static int record_ok(const uint8_t *b,uint32_t cap,uint32_t off,uint32_t *next,uint32_t *namebytes){
    uint32_t n,len;
    if(off>cap||cap-off<104)return 0;
    memcpy(&n,b+off,4);memcpy(&len,b+off+60,4);
    if(!len||(len&1)||len>510||len>cap-off-104)return 0;
    if(n&&(n<104+len||(n&7)||n>cap-off||cap-off-n<104))return 0;
    *next=n;*namebytes=len;return 1;
}
uint32_t ru_dir_abi(void){return RU_DIR_ABI;}
uint32_t ru_dir_event_size(void){return sizeof(RuDirEvent);}
#if defined(_WIN32) && !defined(RU_DIR_PORTABLE_TEST)
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include <windows.h>
#include <shlobj.h>
#include <wchar.h>
typedef char WinEnumerationNameOffset[(offsetof(FILE_ID_BOTH_DIR_INFO,FileName)==104)?1:-1];
/* Local NT definitions use pointer-sized fields, never packed wire layouts. */
typedef struct DirUnicode { USHORT Length,MaximumLength; PWSTR Buffer; } DirUnicode;
typedef struct DirObject { ULONG Length; HANDLE RootDirectory; DirUnicode *ObjectName; ULONG Attributes; PVOID SecurityDescriptor,SecurityQualityOfService; } DirObject;
typedef struct DirIoStatus { union { LONG Status; PVOID Pointer; } u; ULONG_PTR Information; } DirIoStatus;
typedef LONG (NTAPI *DirNtCreate)(PHANDLE,ACCESS_MASK,DirObject*,DirIoStatus*,PLARGE_INTEGER,ULONG,ULONG,ULONG,ULONG,PVOID,ULONG);
#define DIR_ENUM_BYTES 16384u
#define DIR_BAD_ATTR (FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_OFFLINE|0x00040000u|0x00400000u)
typedef struct Frame { HANDLE handle; uint32_t pathUnits; uint8_t bytes[DIR_ENUM_BYTES]; } Frame;
typedef struct Job {
    volatile LONG lock,cancel,release,abandoned,generation;
    HANDLE volatile thread; HMODULE module; DirNtCreate ntcreate;
    uint32_t head,count,sequence,fileSequence,files,dirs,skipped,errors,terminal;
    uint64_t reads; uint16_t root[RU_DIR_PATH_UNITS],path[RU_DIR_PATH_UNITS]; uint32_t rootUnits,pathUnits;
    RuDirEvent queue[RU_DIR_QUEUE_SLOTS]; Frame frames[RU_DIR_DEPTH_LIMIT+1];
    HANDLE ancestors[33];uint32_t ancestorCount;DWORD volume;
} Job;
static Job job;
#ifdef RU_DIR_TESTING
/* Isolated test-DLL substitutions; absent entirely from production builds. */
#include "../tests/directory_io_faults.h"
#endif
#ifndef DIR_NT_CALL
#define DIR_NT_CALL job.ntcreate
#endif
static int take(void){return InterlockedCompareExchange(&job.lock,1,0)==0;}
static void drop(void){InterlockedExchange(&job.lock,0);}
static int cancelled(void){return InterlockedCompareExchange(&job.cancel,0,0)!=0;}
static void event_init(RuDirEvent *e,uint32_t kind,uint32_t reason){
    memset(e,0,sizeof(*e));e->abi=RU_DIR_ABI;e->size=sizeof(*e);e->kind=kind;e->reason=reason;
    e->generation=job.generation;e->fileSequence=job.fileSequence;e->files=job.files;e->dirs=job.dirs;
    e->skipped=job.skipped;e->errors=job.errors;e->readBytes=job.reads;
    e->pathUnits=job.pathUnits;memcpy(e->path,job.path,job.pathUnits*2);
}
static int emit(RuDirEvent *e){
    for(;;){
        if(cancelled())return 0;
        if(take()){
#ifdef RU_DIR_TESTING
            dir_test_hold_queue_lock();
#endif
            if(job.count<RU_DIR_QUEUE_SLOTS){e->sequence=++job.sequence;job.queue[(job.head+job.count)%RU_DIR_QUEUE_SLOTS]=*e;job.count++;drop();return 1;}
            drop();
        }
        Sleep(2);
    }
}
static void skip_scope(uint32_t reason,int error,int directory){
    RuDirEvent e;job.skipped++;if(error)job.errors++;event_init(&e,error?RU_DIR_ERROR:RU_DIR_SKIP,reason);if(error&&job.terminal)e.flags=2;if(directory){e.flags|=4;e.fileSequence=0;}emit(&e);
}
static void skip(uint32_t reason,int error){skip_scope(reason,error,0);}
static void dskip(uint32_t reason,int error){skip_scope(reason,error,1);}
static HANDLE open_nt(HANDLE parent,const uint16_t *name,uint32_t units,int directory){
    HANDLE h=NULL;DirUnicode u;DirObject o;DirIoStatus ios;LONG st;
    if(cancelled()||units>32766)return INVALID_HANDLE_VALUE;
    memset(&o,0,sizeof(o));memset(&ios,0,sizeof(ios));u.Length=(USHORT)(units*2);u.MaximumLength=u.Length;u.Buffer=(PWSTR)name;
    o.Length=sizeof(o);o.RootDirectory=parent;o.ObjectName=&u;
    o.Attributes=0x40u|0x1000u; /* OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE */
    st=DIR_NT_CALL(&h,(directory?FILE_LIST_DIRECTORY:FILE_READ_DATA)|FILE_READ_ATTRIBUTES|SYNCHRONIZE,
        &o,&ios,NULL,0,FILE_SHARE_READ,1,0x00200000u|0x00400000u|0x20u|(directory?1u:0x40u),NULL,0);
    /* FILE_OPEN_REPARSE_POINT | FILE_OPEN_NO_RECALL | synchronous | type.
     * NO_RECALL prevents a raced cloud-placeholder attribute change from
     * silently triggering recall before post-open attribute validation. */
    if(st<0)return INVALID_HANDLE_VALUE;
    if(!h)return INVALID_HANDLE_VALUE;
    return h;
}
static int info(HANDLE h,int directory,BY_HANDLE_FILE_INFORMATION *i){
    if(GetFileType(h)!=FILE_TYPE_DISK||!GetFileInformationByHandle(h,i))return 0;
    if(i->dwFileAttributes&DIR_BAD_ATTR)return 0;
    if(!!(i->dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=!!directory)return 0;
    return 1;
}
static uint64_t size_of(const BY_HANDLE_FILE_INFORMATION *i){return ((uint64_t)i->nFileSizeHigh<<32)|i->nFileSizeLow;}
static uint64_t id_of(const BY_HANDLE_FILE_INFORMATION *i){return ((uint64_t)i->nFileIndexHigh<<32)|i->nFileIndexLow;}
static uint64_t stamp_of(const BY_HANDLE_FILE_INFORMATION *i){return ((uint64_t)i->ftLastWriteTime.dwHighDateTime<<32)|i->ftLastWriteTime.dwLowDateTime;}
static int same(const BY_HANDLE_FILE_INFORMATION *a,const BY_HANDLE_FILE_INFORMATION *b){
    return a->dwVolumeSerialNumber==b->dwVolumeSerialNumber&&id_of(a)==id_of(b)&&size_of(a)==size_of(b)&&stamp_of(a)==stamp_of(b)&&a->dwFileAttributes==b->dwFileAttributes;
}
static void metadata(RuDirEvent *e,const BY_HANDLE_FILE_INFORMATION *i){e->rawSize=size_of(i);e->volume=i->dwVolumeSerialNumber;e->fileId=id_of(i);e->stamp=stamp_of(i);}
static void read_file(HANDLE parent,const uint16_t *name,uint32_t units){
    HANDLE h=open_nt(parent,name,units,0);BY_HANDLE_FILE_INFORMATION before,after;FILE_BASIC_INFO basicBefore,basicAfter;RuDirEvent e;uint64_t offset=0,sz;DWORD got,want;uint8_t probe;
    if(h==INVALID_HANDLE_VALUE){if(!cancelled())skip(RU_DIR_REASON_IO,1);return;}
    if(!info(h,0,&before)||!GetFileInformationByHandleEx(h,FileBasicInfo,&basicBefore,sizeof(basicBefore))||before.dwVolumeSerialNumber!=job.volume){skip(RU_DIR_REASON_UNSAFE,0);goto done;}
    sz=size_of(&before);if(sz>RU_DIR_FILE_BYTES){skip(RU_DIR_REASON_SIZE,0);goto done;}
    event_init(&e,RU_DIR_START,0);metadata(&e,&before);if(!emit(&e))goto done;
    while(offset<sz&&!cancelled()){
        uint64_t remaining=RU_DIR_READ_BYTES-job.reads;
        if(!remaining){job.terminal=RU_DIR_REASON_READ_BUDGET;skip(job.terminal,0);goto done;}
        want=(DWORD)((sz-offset)>RU_DIR_DATA_BYTES?RU_DIR_DATA_BYTES:sz-offset);if(want>remaining)want=(DWORD)remaining;
        event_init(&e,RU_DIR_DATA,0);got=0;
        if(!ReadFile(h,e.data,want,&got,NULL)){if(!cancelled())skip(RU_DIR_REASON_IO,1);goto done;}
        job.reads+=got;
        if(!got){skip(RU_DIR_REASON_CHANGED,0);goto done;}
        e.offset=offset;e.dataBytes=got;e.readBytes=job.reads;metadata(&e,&before);if(!emit(&e))goto done;offset+=got;
    }
    if(cancelled())goto done;
    /* Probe EOF even for an empty file. With no remaining budget there is no
     * legal probe: conservatively skip (no END), even at declared exact size. */
    if(job.reads==RU_DIR_READ_BYTES){job.terminal=RU_DIR_REASON_READ_BUDGET;skip(job.terminal,0);goto done;}
    got=0;if(!ReadFile(h,&probe,1,&got,NULL)){if(!cancelled())skip(RU_DIR_REASON_IO,1);goto done;}
    job.reads+=got;
    if(got||!info(h,0,&after)||!GetFileInformationByHandleEx(h,FileBasicInfo,&basicAfter,sizeof(basicAfter))||
       !same(&before,&after)||basicBefore.ChangeTime.QuadPart!=basicAfter.ChangeTime.QuadPart||
       basicBefore.CreationTime.QuadPart!=basicAfter.CreationTime.QuadPart){skip(RU_DIR_REASON_CHANGED,0);goto done;}
    event_init(&e,RU_DIR_END,0);metadata(&e,&after);e.offset=offset;e.flags=1;emit(&e);
 done:CloseHandle(h);
}
static int append_path(const uint16_t *name,uint32_t units){
    uint32_t slash=job.pathUnits&&job.path[job.pathUnits-1]!='\\';
    if(job.pathUnits+slash+units>=RU_DIR_PATH_UNITS)return 0;
    if(slash)job.path[job.pathUnits++]='\\';
    memcpy(job.path+job.pathUnits,name,units*2);job.pathUnits+=units;job.path[job.pathUnits]=0;return 1;
}
static void walk(HANDLE h,uint32_t depth){
    Frame *f=&job.frames[depth];BOOL first=TRUE;BY_HANDLE_FILE_INFORMATION inf;
    f->handle=h;f->pathUnits=job.pathUnits;
    while(!cancelled()&&!job.terminal){
        uint32_t off=0;memset(f->bytes,0,sizeof(f->bytes));
        if(!GetFileInformationByHandleEx(h,first?FileIdBothDirectoryRestartInfo:FileIdBothDirectoryInfo,f->bytes,sizeof(f->bytes))){
            DWORD err=GetLastError();if(err!=ERROR_NO_MORE_FILES&&!cancelled())dskip(RU_DIR_REASON_ENUMERATION,1);return;
        }
        first=FALSE;
        for(;;){
            uint32_t next,nb,attr,units;uint16_t name[256];HANDLE child;
            if(cancelled()||job.terminal)return;
            if(!record_ok(f->bytes,sizeof(f->bytes),off,&next,&nb)){dskip(RU_DIR_REASON_ENUMERATION,1);return;}
            memcpy(&attr,f->bytes+off+56,4);units=nb/2;memcpy(name,f->bytes+off+104,nb);name[units]=0;
            if(!((units==1&&name[0]=='.')||(units==2&&name[0]=='.'&&name[1]=='.'))){
                int directory=(attr&FILE_ATTRIBUTE_DIRECTORY)!=0;
                if(directory){if(job.dirs==RU_DIR_DIRECTORY_LIMIT){job.terminal=RU_DIR_REASON_DIRECTORIES;dskip(job.terminal,0);return;}job.dirs++;}
                else{if(job.files==RU_DIR_FILE_LIMIT){job.terminal=RU_DIR_REASON_FILES;dskip(job.terminal,0);return;}job.files++;job.fileSequence++;}
                job.pathUnits=f->pathUnits;job.path[job.pathUnits]=0;
                if(!component_ok(name,units)||!append_path(name,units))skip_scope(RU_DIR_REASON_PATH,0,directory);
                else if(attr&DIR_BAD_ATTR)skip_scope(RU_DIR_REASON_UNSAFE,0,directory);
                else if(directory){
                    if(depth==RU_DIR_DEPTH_LIMIT)dskip(RU_DIR_REASON_DEPTH,0);
                    else{
                        child=open_nt(h,name,units,1);
                        if(child==INVALID_HANDLE_VALUE){if(!cancelled())dskip(RU_DIR_REASON_IO,1);}
                        else{if(!info(child,1,&inf)||inf.dwVolumeSerialNumber!=job.volume)skip_scope(RU_DIR_REASON_UNSAFE,0,directory);else walk(child,depth+1);CloseHandle(child);}
                    }
                }else read_file(h,name,units);
                job.pathUnits=f->pathUnits;job.path[job.pathUnits]=0;
            }
            if(!next)break;
            off+=next;
        }
    }
}
static HANDLE establish_root(void){
    WCHAR drive[4],device[256],ntpath[260];uint32_t n,i,start;HANDLE h;BY_HANDLE_FILE_INFORMATION inf;
    drive[0]=(WCHAR)upper16(job.root[0]);drive[1]=':';drive[2]='\\';drive[3]=0;
    if(GetDriveTypeW(drive)!=DRIVE_FIXED)return INVALID_HANDLE_VALUE;
    drive[2]=0;memset(device,0,sizeof(device));
    if(!QueryDosDeviceW(drive,device,256))return INVALID_HANDLE_VALUE;
    /* Refuse SUBST, UNC, LanmanRedirector, devices and unknown mappings. */
    if(wcsncmp(device,L"\\Device\\HarddiskVolume",22)!=0)return INVALID_HANDLE_VALUE;
    n=(uint32_t)wcslen(device);if(n<=22||n>250)return INVALID_HANDLE_VALUE;
    for(i=22;i<n;i++)if(device[i]<'0'||device[i]>'9')return INVALID_HANDLE_VALUE;
    memcpy(ntpath,device,n*2);ntpath[n++]='\\';ntpath[n]=0;
    h=open_nt(NULL,(uint16_t*)ntpath,n,1);if(h==INVALID_HANDLE_VALUE)return h;
    job.ancestors[job.ancestorCount++]=h;
    if(!info(h,1,&inf))return INVALID_HANDLE_VALUE;
    job.volume=inf.dwVolumeSerialNumber;start=3;
    for(i=3;i<=job.rootUnits;i++)if(i==job.rootUnits||job.root[i]=='\\'){
        if(i==start)break;
        h=open_nt(h,job.root+start,i-start,1);if(h==INVALID_HANDLE_VALUE)return h;
        job.ancestors[job.ancestorCount++]=h;
        if(!info(h,1,&inf)||inf.dwVolumeSerialNumber!=job.volume)return INVALID_HANDLE_VALUE;
        start=i+1;
    }
    return h;
}
static DWORD WINAPI run(void *unused){
    HMODULE module=job.module;HANDLE root;RuDirEvent e;(void)unused;
    job.ntcreate=(DirNtCreate)(void*)GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtCreateFile");
    if(!job.ntcreate){job.terminal=RU_DIR_REASON_PLATFORM;dskip(job.terminal,1);}
    else{
        root=establish_root();
        if(root==INVALID_HANDLE_VALUE){job.terminal=RU_DIR_REASON_UNSAFE;if(!cancelled())dskip(job.terminal,1);}
        else{job.dirs=1;walk(root,0);}
    }
    while(job.ancestorCount)CloseHandle(job.ancestors[--job.ancestorCount]);
    if(cancelled())job.terminal=RU_DIR_REASON_CANCELLED;
    event_init(&e,RU_DIR_JOB_END,job.terminal);e.status=job.terminal;emit(&e);
    /* Atomic unload + thread termination. UI will not reuse storage until the
     * thread handle is signaled, so no exit-time context reuse race. */
    for(;;){if(take()){
        if(job.abandoned){HANDLE observer=(HANDLE)InterlockedExchangePointer((PVOID volatile*)&job.thread,NULL);if(observer)CloseHandle(observer);}
        drop();break;
    }Sleep(1);}
    FreeLibraryAndExitThread(module,0);return 0;
}
static void reap(void){
    if(job.thread&&job.release&&WaitForSingleObject(job.thread,0)==WAIT_OBJECT_0){CloseHandle(job.thread);job.thread=NULL;job.count=0;}
}
uint32_t ru_dir_start(uint32_t abi,uint32_t generation,const uint16_t *root,uint32_t units){
    HMODULE pin;HANDLE thread;
    if(abi!=RU_DIR_ABI||!generation||!root_ok(root,units))return RU_DIR_BAD_ARGUMENT;
    if(InterlockedCompareExchange(&job.abandoned,0,0))return RU_DIR_STOPPING;
    if(!take())return RU_DIR_BUSY;
    reap();
    if(job.abandoned){drop();return RU_DIR_STOPPING;}
    if(job.thread){uint32_t result=job.cancel?RU_DIR_STOPPING:RU_DIR_BUSY;drop();return result;}
    if(generation<=(uint32_t)job.generation){drop();return RU_DIR_BAD_ARGUMENT;}
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,(LPCWSTR)(uintptr_t)&ru_dir_start,&pin)){drop();return RU_DIR_SYSTEM_ERROR;}
    /* lock stays held; zero only the worker-owned state after the lock. */
    job.cancel=0;job.release=0;job.module=pin;InterlockedExchange(&job.generation,(LONG)generation);job.head=job.count=job.sequence=job.fileSequence=0;
    job.files=job.dirs=job.skipped=job.errors=job.terminal=0;job.reads=0;job.ancestorCount=0;
    job.rootUnits=job.pathUnits=units;memcpy(job.root,root,units*2);job.root[units]=0;memcpy(job.path,job.root,(units+1)*2);
    thread=CreateThread(NULL,0,run,NULL,0,NULL);
    if(!thread){FreeLibrary(pin);drop();return RU_DIR_SYSTEM_ERROR;}
    job.thread=thread;drop();return RU_DIR_OK;
}
uint32_t ru_dir_poll(uint32_t abi,uint32_t generation,RuDirEvent *out,uint32_t bytes){
    if(abi!=RU_DIR_ABI||!out||bytes!=sizeof(*out)||!generation)return RU_DIR_BAD_ARGUMENT;
    if(!take())return RU_DIR_BUSY;
    if(!job.thread||generation!=(uint32_t)job.generation||job.release){drop();return RU_DIR_BAD_ARGUMENT;}
    if(!job.count){drop();return RU_DIR_EMPTY;}
    *out=job.queue[job.head];job.head=(job.head+1)%RU_DIR_QUEUE_SLOTS;job.count--;drop();return RU_DIR_OK;
}
static uint32_t stop(uint32_t abi,uint32_t generation,int release){
    if(abi!=RU_DIR_ABI||!generation)return RU_DIR_BAD_ARGUMENT;
    if(!take())return RU_DIR_BUSY;
    if(!job.thread||generation!=(uint32_t)job.generation){drop();return RU_DIR_BAD_ARGUMENT;}
    InterlockedExchange(&job.cancel,1);if(release){InterlockedExchange(&job.release,1);job.count=0;}
    CancelSynchronousIo(job.thread);drop();return RU_DIR_OK;
}
uint32_t ru_dir_cancel(uint32_t abi,uint32_t generation){return stop(abi,generation,0);}
uint32_t ru_dir_release(uint32_t abi,uint32_t generation){return stop(abi,generation,1);}
uint32_t ru_dir_status(uint32_t abi){
    uint32_t s;if(abi!=RU_DIR_ABI||!take())return UINT32_MAX;reap();
    s=!job.thread?RU_DIR_IDLE:WaitForSingleObject(job.thread,0)==WAIT_OBJECT_0?RU_DIR_FINISHED:job.cancel?RU_DIR_DRAINING:RU_DIR_ACTIVE;
    drop();return s;
}
uint32_t ru_dir_abandon(uint32_t abi,uint32_t generation){
    HANDLE observer;
    /* All public entry points are serialized by the owning UI thread. A
     * worker never changes generation; stale callers cannot stop a new job. */
    if(abi!=RU_DIR_ABI||!generation||generation!=(uint32_t)InterlockedCompareExchange(&job.generation,0,0))return RU_DIR_BAD_ARGUMENT;
    InterlockedExchange(&job.abandoned,1);
    InterlockedExchange(&job.cancel,1);
    InterlockedExchange(&job.release,1);
    /* Claim ownership atomically, independent of queue-lock contention. This
     * also closes the race with a worker already doing its final cleanup.
     * Closing an observer does not terminate the independently pinned worker. */
    observer=(HANDLE)InterlockedExchangePointer((PVOID volatile*)&job.thread,NULL);
    if(observer){CancelSynchronousIo(observer);CloseHandle(observer);}
    if(take()){job.count=0;drop();}
    return RU_DIR_OK;
}
uint32_t ru_dir_pick_folder(uint64_t owner,uint16_t *out,uint32_t capacity){
    HRESULT hr;BROWSEINFOW bi;PIDLIST_ABSOLUTE pidl;WCHAR path[RU_DIR_PATH_UNITS];uint32_t result=RU_DIR_CANCELLED;
    typedef BOOL (WINAPI *Extract)(PCIDLIST_ABSOLUTE,PWSTR,DWORD,DWORD);Extract extract;
    if(!out||capacity<RU_DIR_PATH_UNITS)return RU_DIR_BAD_ARGUMENT;
    out[0]=0;
    hr=CoInitializeEx(NULL,COINIT_APARTMENTTHREADED);
    if(FAILED(hr))return RU_DIR_SYSTEM_ERROR;
    extract=(Extract)(void*)GetProcAddress(GetModuleHandleW(L"shell32.dll"),"SHGetPathFromIDListEx");
    if(!extract){CoUninitialize();return RU_DIR_UNSUPPORTED;}
    memset(&bi,0,sizeof(bi));bi.hwndOwner=(HWND)(uintptr_t)owner;
    bi.lpszTitle=NULL;bi.ulFlags=BIF_RETURNONLYFSDIRS|BIF_NEWDIALOGSTYLE|BIF_EDITBOX;
    pidl=SHBrowseForFolderW(&bi);
    if(pidl){memset(path,0,sizeof(path));
        if(!extract(pidl,path,RU_DIR_PATH_UNITS,0))result=RU_DIR_BAD_ARGUMENT;
        else{uint32_t n=(uint32_t)wcslen(path);
            if(!root_ok((uint16_t*)path,n))result=RU_DIR_BAD_ARGUMENT;
            else{memcpy(out,path,(n+1)*2);result=RU_DIR_OK;}
        }
        CoTaskMemFree(pidl);
    }
    CoUninitialize();return result;
}

#else
uint32_t ru_dir_start(uint32_t a,uint32_t g,const uint16_t *p,uint32_t n){return a!=RU_DIR_ABI||!g||!root_ok(p,n)?RU_DIR_BAD_ARGUMENT:RU_DIR_UNSUPPORTED;}
uint32_t ru_dir_poll(uint32_t a,uint32_t g,RuDirEvent *e,uint32_t n){return a!=RU_DIR_ABI||!g||!e||n!=sizeof(*e)?RU_DIR_BAD_ARGUMENT:RU_DIR_UNSUPPORTED;}
uint32_t ru_dir_cancel(uint32_t a,uint32_t g){return a!=RU_DIR_ABI||!g?RU_DIR_BAD_ARGUMENT:RU_DIR_UNSUPPORTED;}
uint32_t ru_dir_release(uint32_t a,uint32_t g){return ru_dir_cancel(a,g);}
uint32_t ru_dir_status(uint32_t a){return a==RU_DIR_ABI?RU_DIR_IDLE:UINT32_MAX;}
uint32_t ru_dir_abandon(uint32_t a,uint32_t g){return ru_dir_cancel(a,g);}
uint32_t ru_dir_pick_folder(uint64_t owner,uint16_t *out,uint32_t cap){(void)owner;if(!out||cap<RU_DIR_PATH_UNITS)return RU_DIR_BAD_ARGUMENT;out[0]=0;return RU_DIR_UNSUPPORTED;}
#endif
