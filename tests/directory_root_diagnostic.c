/* NOT ACCEPTED: test-only synchronous root establishment probe.
 * Includes the production implementation unchanged. Wrappers call each real
 * OS API once, recording numbers only. The explicit POSTCHECK variant changes
 * only the directory type option; every no-follow/no-recall and postcheck stays.
 * Never starts a worker, enumerates a directory, or reads a file payload.
 * Build each policy with RU_DIR_ROOT_CONTROL to omit observation wrappers.
 * RU_DIR_ROOT_POSTCHECK is a hypothesis probe, never a production fallback.
 */
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include <windows.h>
#include <shlobj.h>
#include <winternl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <wchar.h>
static uint32_t checked_options(uint32_t options,uint32_t attributes,uint32_t share,uint32_t disposition,uint32_t access){
    /* Refuse unexpected inputs without making a modified native call. */
    if(options!=0x00600021u||attributes!=0x1040u||share!=1u||disposition!=1u||access!=0x00100081u)exit(5);
#ifdef RU_DIR_ROOT_POSTCHECK
    return options&~1u;
#else
    return options;
#endif
}
#ifndef RU_DIR_ROOT_CONTROL
/* api: 1 drive type; 2 DOS mapping; 3 NT open; 4 type; 5 file info.
 * component: 0 volume root, then anonymous 1-based ancestor ordinal.
 * mapping: 0 not observed, 1 wrong prefix, 2 wrong suffix, 3 allowed form.
 * Win32 last-error is valid only where the API documents a failing result.
 */
typedef struct Observation {
    uint32_t api,component,result,win32_valid,win32_code,nt_valid,nt_code;
    uint32_t mapping,attributes,same_volume,handle_present;
    uint32_t requested_options,effective_options,object_flags,share_access,disposition,desired_access;
} Observation;
static Observation observations[128];
static uint32_t observation_count,observation_overflow,opens,first_volume,have_volume;
static Observation *note(uint32_t api,uint32_t result){
    static Observation overflow;
    Observation *o;
    if(observation_count>=128){observation_overflow=1;o=&overflow;}
    else o=&observations[observation_count++];
    memset(o,0,sizeof(*o));o->api=api;o->component=opens?opens-1:0;o->result=result;return o;
}
static UINT WINAPI observe_drive(LPCWSTR path){
    UINT result=GetDriveTypeW(path);note(1,result);return result;
}
static DWORD WINAPI observe_mapping(LPCWSTR name,LPWSTR target,DWORD capacity){
    DWORD result=QueryDosDeviceW(name,target,capacity),error=result?0:GetLastError();
    Observation *o=note(2,result);
    if(!result){o->win32_valid=1;o->win32_code=error;SetLastError(error);}
    else{
        size_t n=wcslen(target),i;o->mapping=1;
        if(wcsncmp(target,L"\\Device\\HarddiskVolume",22)==0){
            o->mapping=2;
            if(n>22&&n<=250){o->mapping=3;for(i=22;i<n;i++)if(target[i]<'0'||target[i]>'9')o->mapping=2;}
        }
    }
    return result;
}
static LONG observe_nt(PHANDLE handle,LONG result,uint32_t requested,uint32_t effective,uint32_t attributes,uint32_t share,uint32_t disposition,uint32_t access){
    Observation *o;opens++;o=note(3,(uint32_t)result);o->nt_valid=1;o->nt_code=(uint32_t)result;o->handle_present=*handle!=NULL;
    o->requested_options=requested;o->effective_options=effective;o->object_flags=attributes;o->share_access=share;o->disposition=disposition;o->desired_access=access;return result;
}
static DWORD WINAPI observe_type(HANDLE handle){
    DWORD result,error;Observation *o;
    /* Documented disambiguation for FILE_TYPE_UNKNOWN; return is unchanged. */
    SetLastError(ERROR_SUCCESS);result=GetFileType(handle);error=GetLastError();
    o=note(4,result);if(result==FILE_TYPE_UNKNOWN){o->win32_valid=1;o->win32_code=error;}
    SetLastError(error);return result;
}
static BOOL WINAPI observe_info(HANDLE handle,LPBY_HANDLE_FILE_INFORMATION information){
    BOOL result=GetFileInformationByHandle(handle,information);DWORD error=result?0:GetLastError();
    Observation *o=note(5,(uint32_t)result);
    if(!result){o->win32_valid=1;o->win32_code=error;SetLastError(error);}
    else{
        if(!have_volume){first_volume=information->dwVolumeSerialNumber;have_volume=1;}
        o->attributes=information->dwFileAttributes;o->same_volume=information->dwVolumeSerialNumber==first_volume;
    }
    return result;
}
#define GetDriveTypeW observe_drive
#define QueryDosDeviceW observe_mapping
#define GetFileType observe_type
#define GetFileInformationByHandle observe_info
#define DIR_NT_CALL(handle,access,object,ios,allocation,attributes,share,disposition,options,ea,eabytes) \
    observe_nt(handle,job.ntcreate(handle,access,object,ios,allocation,attributes,share,disposition,checked_options(options,(object)->Attributes,share,disposition,access),ea,eabytes),options,checked_options(options,(object)->Attributes,share,disposition,access),(object)->Attributes,share,disposition,access)
#else
#define DIR_NT_CALL(handle,access,object,ios,allocation,attributes,share,disposition,options,ea,eabytes) \
    job.ntcreate(handle,access,object,ios,allocation,attributes,share,disposition,checked_options(options,(object)->Attributes,share,disposition,access),ea,eabytes)
#endif
/* No copied/reimplemented root-opening or safety policy. */
#include "../native/ru_directory_io.c"
/* Compile-time comparison with the selected Windows SDK, not guessed packing. */
#define ABI_SIZE(a,b) typedef char abi_size_##a[(sizeof(a)==sizeof(b))?1:-1]
#define ABI_FIELD(a,af,b,bf) typedef char abi_field_##a##_##af[(offsetof(a,af)==offsetof(b,bf))?1:-1]
ABI_SIZE(DirUnicode,UNICODE_STRING);
ABI_FIELD(DirUnicode,Length,UNICODE_STRING,Length);
ABI_FIELD(DirUnicode,MaximumLength,UNICODE_STRING,MaximumLength);
ABI_FIELD(DirUnicode,Buffer,UNICODE_STRING,Buffer);
ABI_SIZE(DirObject,OBJECT_ATTRIBUTES);
ABI_FIELD(DirObject,Length,OBJECT_ATTRIBUTES,Length);
ABI_FIELD(DirObject,RootDirectory,OBJECT_ATTRIBUTES,RootDirectory);
ABI_FIELD(DirObject,ObjectName,OBJECT_ATTRIBUTES,ObjectName);
ABI_FIELD(DirObject,Attributes,OBJECT_ATTRIBUTES,Attributes);
ABI_FIELD(DirObject,SecurityDescriptor,OBJECT_ATTRIBUTES,SecurityDescriptor);
ABI_FIELD(DirObject,SecurityQualityOfService,OBJECT_ATTRIBUTES,SecurityQualityOfService);
ABI_SIZE(DirIoStatus,IO_STATUS_BLOCK);
ABI_FIELD(DirIoStatus,u,IO_STATUS_BLOCK,Status);
ABI_FIELD(DirIoStatus,Information,IO_STATUS_BLOCK,Information);
int wmain(int argc,WCHAR **argv){
    HANDLE root;uint32_t units,established;
    if(argc!=2)return 2;
    units=(uint32_t)wcslen(argv[1]);if(!root_ok((const uint16_t*)argv[1],units))return 3;
    job.ntcreate=(DirNtCreate)(void*)GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtCreateFile");
    if(!job.ntcreate)return 4;
    job.rootUnits=units;memcpy(job.root,argv[1],(units+1)*2);
    root=establish_root();established=root!=INVALID_HANDLE_VALUE;
    while(job.ancestorCount)CloseHandle(job.ancestors[--job.ancestorCount]);
    printf("{\"schema\":\"ru-directory-root-observation-v1\",\"root_established\":%s,\"trace_overflow\":",established?"true":"false");
#ifdef RU_DIR_ROOT_CONTROL
    printf("false,\"instrumented\":false,\"trace\":[]}");
#else
    {
        uint32_t i;
        printf("%s,\"instrumented\":true,\"trace\":[",observation_overflow?"true":"false");
        for(i=0;i<observation_count;i++){
            Observation *o=&observations[i];
            printf("%s{\"api\":%u,\"component\":%u,\"result\":%u,\"win32_valid\":%u,\"win32_code\":%u,\"nt_valid\":%u,\"nt_code\":%u,\"mapping\":%u,\"attributes\":%u,\"same_volume\":%u,\"handle_present\":%u,\"requested_options\":%u,\"effective_options\":%u,\"object_flags\":%u,\"share_access\":%u,\"disposition\":%u,\"desired_access\":%u}",i?",":"",o->api,o->component,o->result,o->win32_valid,o->win32_code,o->nt_valid,o->nt_code,o->mapping,o->attributes,o->same_volume,o->handle_present,o->requested_options,o->effective_options,o->object_flags,o->share_access,o->disposition,o->desired_access);
        }
        printf("]}");
    }
#endif
    puts("");return 0;
}
