/* Portable structural checks + actual Windows transport integration host.
 * Portable success is never a substitute for --windows security acceptance. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "../native/ru_directory_io.h"
#ifdef RU_DIR_PORTABLE_TEST
#include "../native/ru_directory_io.c"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static uint32_t wide(const char *s,uint16_t *w){uint32_t n=0;while(*s)w[n++]=(unsigned char)*s++;return n;}
int main(void){
    uint16_t w[1024];uint8_t record[1024];uint32_t n,next,len;RuDirEvent e;
    const char *bad[]={"", "C:","C:foo","\\\\server\\share","\\\\?\\C:\\x","C:\\..","C:\\a\\..", "C:\\a\\", "C:\\a:b","C:\\a.","C:\\a ","C:\\CON","C:\\aux.txt","C:\\COM1.log","C:\\LPT9","C:\\CONIN$","C:\\CONOUT$","C:\\\\a","C:\\a/b","C:\\x*"};size_t i;
    CHECK(sizeof(e)==8192&&offsetof(RuDirEvent,path)==112&&offsetof(RuDirEvent,data)==2160);
    CHECK(ru_dir_abi()==RU_DIR_ABI&&ru_dir_event_size()==8192);
    for(i=0;i<sizeof(bad)/sizeof(*bad);i++){n=wide(bad[i],w);CHECK(!root_ok(w,n));}
    n=wide("C:\\",w);CHECK(root_ok(w,n));n=wide("D:\\normal\\hello.txt",w);CHECK(root_ok(w,n));
    w[0]='x';w[1]=0xd800;CHECK(!component_ok(w,2));w[1]=0xdc00;CHECK(!component_ok(w,2));w[1]=0xd800;w[2]=0xdc00;CHECK(component_ok(w,3));
    n=wide("COM",w);w[n++]=0xb9;CHECK(!component_ok(w,n));
    memset(record,0,sizeof(record));n=2;memcpy(record+60,&n,4);record[104]='x';CHECK(record_ok(record,sizeof(record),0,&next,&len)&&next==0&&len==2);
    n=112;memcpy(record,&n,4);CHECK(record_ok(record,sizeof(record),0,&next,&len));
    n=105;memcpy(record,&n,4);CHECK(!record_ok(record,sizeof(record),0,&next,&len));
    n=1024;memcpy(record,&n,4);CHECK(!record_ok(record,sizeof(record),0,&next,&len));
    n=0;memcpy(record,&n,4);n=511;memcpy(record+60,&n,4);CHECK(!record_ok(record,sizeof(record),0,&next,&len));
    CHECK(!record_ok(record,sizeof(record),1020,&next,&len));
    n=wide("C:\\safe",w);CHECK(ru_dir_start(0,1,w,n)==RU_DIR_BAD_ARGUMENT);CHECK(ru_dir_start(RU_DIR_ABI,1,w,n)==RU_DIR_UNSUPPORTED);
    CHECK(ru_dir_poll(RU_DIR_ABI,1,&e,8191)==RU_DIR_BAD_ARGUMENT);CHECK(ru_dir_status(0)==UINT32_MAX);
    puts("portable layout, root/component and enumeration-record checks PASS; Windows acceptance NOT RUN");return 0;
}
#else
#include <windows.h>
typedef uint32_t (*Start)(uint32_t,uint32_t,const uint16_t*,uint32_t);
typedef uint32_t (*Poll)(uint32_t,uint32_t,RuDirEvent*,uint32_t);
typedef uint32_t (*Stop)(uint32_t,uint32_t);
typedef uint32_t (*Status)(uint32_t);
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s (WinErr %lu)\n",__LINE__,#x,GetLastError());return 1;}}while(0)
int wmain(int argc,WCHAR **argv){
    HMODULE dll;Start start;Poll poll;Stop cancel,release,abandon;Status status;RuDirEvent e;
    uint32_t r,seq=0,active=0,starts=0,ends=0,skips=0,directorySkips=0,fileSkips=0,reasonCounts[13]={0},sentinelSeen=0;uint64_t offset=0,size=0;DWORD deadline;
    HANDLE expected=INVALID_HANDLE_VALUE;uint8_t expectedBytes[RU_DIR_DATA_BYTES];DWORD expectedCount;
    CHECK(argc>=4);dll=LoadLibraryW(argv[1]);CHECK(dll);
    start=(Start)(void*)GetProcAddress(dll,"ru_dir_start");poll=(Poll)(void*)GetProcAddress(dll,"ru_dir_poll");
    cancel=(Stop)(void*)GetProcAddress(dll,"ru_dir_cancel");release=(Stop)(void*)GetProcAddress(dll,"ru_dir_release");
    abandon=(Stop)(void*)GetProcAddress(dll,"ru_dir_abandon");status=(Status)(void*)GetProcAddress(dll,"ru_dir_status");CHECK(start&&poll&&cancel&&release&&abandon&&status);
    if(argc==5){
        typedef uint32_t (*Fault)(uint32_t);Fault fault=(Fault)(void*)GetProcAddress(dll,"ru_dir_test_fault");
        CHECK(fault&&fault((uint32_t)wcstoul(argv[4],NULL,10))==RU_DIR_OK);
    }
    CHECK(start(RU_DIR_ABI,1,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_OK);
    CHECK(start(RU_DIR_ABI,2,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_BUSY);
    if(!wcscmp(argv[3],L"abandon-once")){
        typedef uint32_t (*Held)(void);Held held=(Held)(void*)GetProcAddress(dll,"ru_dir_test_lock_held");CHECK(held);
        deadline=GetTickCount()+10000;
        while(!held()){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(1);}
        CHECK(abandon(RU_DIR_ABI,2)==RU_DIR_BAD_ARGUMENT);CHECK(held());
        /* Exactly one shutdown call. No polling, stop retries, or lock release
         * helper may rescue this path; worker must retire autonomously. */
        CHECK(abandon(RU_DIR_ABI,1)==RU_DIR_OK);
        CHECK(start(RU_DIR_ABI,2,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_STOPPING);
        FreeLibrary(dll);
        while(GetModuleHandleW(argv[1])){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(1);}
        puts("one-shot abandon under worker-owned queue lock/module retirement PASS");return 0;
    }
    if(!wcscmp(argv[3],L"unload")){
        /* Saturated worker must pin its module after caller reference drops. */
        Sleep(100);FreeLibrary(dll);Sleep(100);dll=LoadLibraryW(argv[1]);CHECK(dll);
        CHECK((void*)start==(void*)GetProcAddress(dll,"ru_dir_start"));
    }
    if(!wcscmp(argv[3],L"rapid")){
        uint32_t gen;
        for(gen=1;gen<=100;gen++){
            if(gen>1){CHECK(start(RU_DIR_ABI,gen,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_OK);}
            do{r=cancel(RU_DIR_ABI,gen);}while(r==RU_DIR_BUSY);CHECK(r==RU_DIR_OK);
            CHECK(cancel(RU_DIR_ABI,gen+1)==RU_DIR_BAD_ARGUMENT);
            do{r=release(RU_DIR_ABI,gen);}while(r==RU_DIR_BUSY);CHECK(r==RU_DIR_OK);
            deadline=GetTickCount()+10000;
            while(status(RU_DIR_ABI)!=RU_DIR_IDLE){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(1);}
            CHECK(start(RU_DIR_ABI,gen,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_BAD_ARGUMENT);
        }
        FreeLibrary(dll);puts("rapid 100 cancel/release/restart cycles PASS");return 0;
    }
    if(!wcscmp(argv[3],L"cancel")||!wcscmp(argv[3],L"unload")){
        Sleep(200); /* force bounded queue saturation before cancellation */
        if(argc==5&&wcstoul(argv[4],NULL,10)==4){
            typedef uint32_t (*Reads)(void);Reads reads=(Reads)(void*)GetProcAddress(dll,"ru_dir_test_reads");CHECK(reads);
            deadline=GetTickCount()+10000;
            while(!reads()){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(1);}
        }
        do{r=cancel(RU_DIR_ABI,1);}while(r==RU_DIR_BUSY);CHECK(r==RU_DIR_OK);
        r=start(RU_DIR_ABI,2,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]));CHECK(r==RU_DIR_STOPPING||r==RU_DIR_BUSY);
        do{r=release(RU_DIR_ABI,1);}while(r==RU_DIR_BUSY);CHECK(r==RU_DIR_OK);
        deadline=GetTickCount()+10000;while(status(RU_DIR_ABI)!=RU_DIR_IDLE){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(2);}
        CHECK(start(RU_DIR_ABI,1,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_BAD_ARGUMENT);
        CHECK(start(RU_DIR_ABI,2,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_OK);
        CHECK(abandon(RU_DIR_ABI,2)==RU_DIR_OK);
        CHECK(start(RU_DIR_ABI,3,(uint16_t*)argv[2],(uint32_t)wcslen(argv[2]))==RU_DIR_STOPPING);
        FreeLibrary(dll);deadline=GetTickCount()+10000;
        while(GetModuleHandleW(argv[1])){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(1);}
        puts("cancel/full queue/restart/abandon/module-retirement PASS");return 0;
    }
    deadline=GetTickCount()+60000;
    for(;;){
        CHECK((LONG)(deadline-GetTickCount())>0);r=poll(RU_DIR_ABI,1,&e,sizeof(e));
        if(r==RU_DIR_EMPTY||r==RU_DIR_BUSY){Sleep(1);continue;}CHECK(r==RU_DIR_OK);
        CHECK(e.abi==RU_DIR_ABI&&e.size==sizeof(e)&&e.generation==1&&e.sequence==++seq&&e.pathUnits<1024&&e.dataBytes<=4096);
        if(e.kind==RU_DIR_START){CHECK(!active);active=e.fileSequence;size=e.rawSize;offset=0;starts++;
            if(!wcscmp(argv[3],L"safe")){
                /* Independent byte-for-byte read of immutable, locally created
                 * regular fixtures. Never used on adversarial traversal modes. */
                CHECK(e.path[e.pathUnits]==0);
                expected=CreateFileW((LPCWSTR)e.path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,NULL);
                CHECK(expected!=INVALID_HANDLE_VALUE);
            }
        }
        else if(e.kind==RU_DIR_DATA){CHECK(active==e.fileSequence&&e.offset==offset&&e.dataBytes>0);offset+=e.dataBytes;CHECK(offset<=size);
            if(expected!=INVALID_HANDLE_VALUE){expectedCount=0;CHECK(ReadFile(expected,expectedBytes,e.dataBytes,&expectedCount,NULL));CHECK(expectedCount==e.dataBytes&&memcmp(expectedBytes,e.data,e.dataBytes)==0);}
            /* Outside-tree adversarial fixture must never be transported. */
            if(e.dataBytes>=24&&!memcmp(e.data,"OUTSIDE_ROOT_MUST_NOT_READ",24))sentinelSeen=1;
            CHECK(!wcscmp(argv[3],L"positive-outside")||!sentinelSeen);}
        else if(e.kind==RU_DIR_END){CHECK(active==e.fileSequence&&offset==size&&e.rawSize==size&&e.flags==1);
            if(expected!=INVALID_HANDLE_VALUE){expectedCount=0;CHECK(ReadFile(expected,expectedBytes,1,&expectedCount,NULL)&&expectedCount==0);CHECK(CloseHandle(expected));expected=INVALID_HANDLE_VALUE;}
            active=0;ends++;}
        else if(e.kind==RU_DIR_SKIP||e.kind==RU_DIR_ERROR){
            CHECK(e.reason>0&&e.reason<=12);reasonCounts[e.reason]++;skips++;
            if(e.flags&4){CHECK(e.fileSequence==0);directorySkips++;}
            else {if(active)CHECK(active==e.fileSequence);active=0;fileSkips++;}
        }
        else if(e.kind==RU_DIR_JOB_END){CHECK(!active);break;}else CHECK(0);
    }
    if(!wcscmp(argv[3],L"safe")){CHECK(starts>=2&&ends==starts&&e.status==0);}
    else if(!wcscmp(argv[3],L"reject")){CHECK(starts==0&&ends==0&&skips>0);}
    else if(!wcscmp(argv[3],L"links")){CHECK(skips>=2&&ends>=2);}
    else if(!wcscmp(argv[3],L"positive-outside")){CHECK(starts==1&&ends==1&&e.status==0&&e.readBytes>24&&sentinelSeen);}
    else if(wcscmp(argv[3],L"scan"))CHECK(0);
    do{r=release(RU_DIR_ABI,1);}while(r==RU_DIR_BUSY);CHECK(r==RU_DIR_OK);
    while(status(RU_DIR_ABI)!=RU_DIR_IDLE){CHECK((LONG)(deadline-GetTickCount())>0);Sleep(1);}
    FreeLibrary(dll);
    printf("{\"starts\":%u,\"ends\":%u,\"skips\":%u,\"directorySkips\":%u,\"fileSkips\":%u,\"files\":%u,\"dirs\":%u,\"status\":%u,\"reads\":%llu,\"reasons\":[",starts,ends,skips,directorySkips,fileSkips,e.files,e.dirs,e.status,(unsigned long long)e.readBytes);
    for(r=0;r<13;r++)printf("%s%u",r?",":"",reasonCounts[r]);
    puts("]}");return 0;
}
#endif
