/* TEST DLL ONLY. Never included or exported in production builds.
 * These are call-level substitutions, not claims about real cloud drivers or
 * kernel-device stalls. Traversal, security gates, cancellation, queue and
 * module ownership remain the same production implementation. */
#ifndef RU_DIR_TESTING
#error Test substitutions require an explicit test-only build
#endif
static volatile LONG dir_test_mode,dir_test_read_calls,dir_test_locked;
__declspec(dllexport) uint32_t ru_dir_test_lock_held(void){return (uint32_t)InterlockedCompareExchange(&dir_test_locked,0,0);}
static void dir_test_hold_queue_lock(void){
    if(dir_test_mode==6){
        InterlockedExchange(&dir_test_locked,1);
        while(!InterlockedCompareExchange(&job.cancel,0,0))Sleep(1);
        InterlockedExchange(&dir_test_locked,0);
    }
}
__declspec(dllexport) uint32_t ru_dir_test_reads(void){return (uint32_t)InterlockedCompareExchange(&dir_test_read_calls,0,0);}
__declspec(dllexport) uint32_t ru_dir_test_fault(uint32_t mode){
    if(mode>6||job.thread)return RU_DIR_BAD_ARGUMENT;
    InterlockedExchange(&dir_test_mode,(LONG)mode);return RU_DIR_OK;
}
static UINT WINAPI test_drive_type(LPCWSTR path){
    return dir_test_mode==1?DRIVE_REMOTE:GetDriveTypeW(path);
}
static BOOL WINAPI test_file_info(HANDLE handle,LPBY_HANDLE_FILE_INFORMATION information){
    BOOL ok=GetFileInformationByHandle(handle,information);
    if(ok&&dir_test_mode==2)information->dwFileAttributes|=FILE_ATTRIBUTE_OFFLINE;
    if(ok&&dir_test_mode==3)information->dwFileAttributes|=0x00400000u;
    return ok;
}
static BOOL WINAPI test_read(HANDLE handle,LPVOID data,DWORD size,LPDWORD got,LPOVERLAPPED overlap){
    InterlockedIncrement(&dir_test_read_calls);
    if(dir_test_mode==4){
        /* Controlled stalled-call model: cancellation must unblock ownership
         * cleanup, not terminate a thread or start an overlapping replacement. */
        while(!InterlockedCompareExchange(&job.cancel,0,0))Sleep(1);
        *got=0;SetLastError(ERROR_OPERATION_ABORTED);return FALSE;
    }
    return ReadFile(handle,data,size,got,overlap);
}
static LONG NTAPI test_nt_create(PHANDLE handle,ACCESS_MASK access,DirObject *object,DirIoStatus *ios,
    PLARGE_INTEGER allocation,ULONG attributes,ULONG sharing,ULONG disposition,ULONG options,PVOID ea,ULONG eaBytes){
    if(!(options&0x00400000u)||!(options&0x00200000u)||!(object->Attributes&0x1000u)||sharing!=FILE_SHARE_READ)
        return (LONG)0xc000000du;
    /* Simulate provider changing to a reparse object immediately before open. */
    if(dir_test_mode==5)return (LONG)0xc000050bu;
    return job.ntcreate(handle,access,object,ios,allocation,attributes,sharing,disposition,options,ea,eaBytes);
}
#define GetDriveTypeW test_drive_type
#define GetFileInformationByHandle test_file_info
#define ReadFile test_read
#define DIR_NT_CALL test_nt_create
