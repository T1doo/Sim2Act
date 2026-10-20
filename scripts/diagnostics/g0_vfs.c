/* Engineering-only SQLite VFS boundary. No SQLite library is linked here.
 * Stable public ABI declarations below follow SQLite's public-domain headers:
 * https://sqlite.org/c3ref/vfs.html /c3ref/io_methods.html
 * Installed with pointers from the *same* loaded CPython _sqlite3 library.
 * Only Linux unix VFS v3 is accepted; unknown operations fail closed.
 */
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <sys/stat.h>

typedef int64_t I64;
typedef struct File File;
typedef struct Methods Methods;
typedef struct Vfs Vfs;
struct File { const Methods *pMethods; };
struct Methods {
 int iVersion;
 int (*close)(File*); int (*read)(File*,void*,int,I64);
 int (*write)(File*,const void*,int,I64); int (*truncate)(File*,I64);
 int (*sync)(File*,int); int (*size)(File*,I64*);
 int (*lock)(File*,int); int (*unlock)(File*,int); int (*reserved)(File*,int*);
 int (*control)(File*,int,void*); int (*sector)(File*); int (*device)(File*);
 int (*shmmap)(File*,int,int,int,void volatile**);
 int (*shmlock)(File*,int,int,int); void (*shmbarrier)(File*); int (*shmunmap)(File*,int);
 int (*fetch)(File*,I64,int,void**); int (*unfetch)(File*,I64,void*);
};
struct Vfs {
 int iVersion, szOsFile, mxPathname; Vfs *pNext; const char *zName; void *pAppData;
 int (*open)(Vfs*,const char*,File*,int,int*); int (*del)(Vfs*,const char*,int);
 int (*access)(Vfs*,const char*,int,int*); int (*full)(Vfs*,const char*,int,char*);
 void *(*dlopen)(Vfs*,const char*); void (*dlerror)(Vfs*,int,char*);
 void (*(*dlsym)(Vfs*,void*,const char*))(void); void (*dlclose)(Vfs*,void*);
 int (*random)(Vfs*,int,char*); int (*sleep)(Vfs*,int); int (*now)(Vfs*,double*);
 int (*error)(Vfs*,int,char*); int (*now64)(Vfs*,I64*);
 int (*setsys)(Vfs*,const char*,void(*)(void)); void (*(*getsys)(Vfs*,const char*))(void);
 const char *(*nextsys)(Vfs*,const char*);
};
typedef struct { File file; File *real; int slot, mapped; } GuardFile;
static Vfs *base, proxy;
static char paths[4][4096];
static I64 cap;
static int fault, handles[4], maps;
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
enum { OK=0, IOERR=10, NOTFOUND=12, FULL=13, CANTOPEN=14 };
static int fail(int code) { pthread_mutex_lock(&mutex); if (!fault) fault=code;
 pthread_mutex_unlock(&mutex); return IOERR; }
static int failed(void){pthread_mutex_lock(&mutex);int f=fault;pthread_mutex_unlock(&mutex);return f;}
static int slot(const char *s) { if (s) for(int i=0;i<4;i++) if(!strcmp(s,paths[i])) return i; return -1; }
static int valid_size(I64 at, int n) { return at>=0 && n>=0 && at<=cap && (I64)n<=cap-at; }
static int inode_ok(const char *p) { struct stat s;
 if(lstat(p,&s)) return 1; /* xOpen delegates actual errno */
 return S_ISREG(s.st_mode) && s.st_nlink==1 && s.st_size>=0 && (I64)s.st_size<=cap;
}
static GuardFile *g(File *f) { return (GuardFile*)f; }
#define R(f) (g(f)->real)
#define M(f) (R(f)->pMethods)
static int close_file(File *f) {
 GuardFile *p=g(f); pthread_mutex_lock(&mutex);int rc=M(f)->close(R(f));
 if(rc==OK){handles[p->slot]--;if(p->mapped)maps--;free(p->real);p->real=NULL;}
 else if(!fault)fault=8; /* Retain a failed-close slot; no future open/write. */
 pthread_mutex_unlock(&mutex);p->file.pMethods=NULL;return rc;
}
static int read_file(File*f,void*b,int n,I64 o){return M(f)->read(R(f),b,n,o);}
static int write_file(File*f,const void*b,int n,I64 o){
 if(failed())return IOERR;
 if(!valid_size(o,n)) {fail(2);return FULL;} return M(f)->write(R(f),b,n,o);}
static int truncate_file(File*f,I64 n){if(failed())return IOERR;if(n<0||n>cap){fail(2);return FULL;}return M(f)->truncate(R(f),n);}
static int sync_file(File*f,int a){return M(f)->sync(R(f),a);}
static int size_file(File*f,I64*n){return M(f)->size(R(f),n);}
static int lock_file(File*f,int a){return M(f)->lock(R(f),a);}
static int unlock_file(File*f,int a){return M(f)->unlock(R(f),a);}
static int reserved_file(File*f,int*a){return M(f)->reserved(R(f),a);}
static int control_file(File*f,int op,void*a){
 /* LOCKSTATE is read-only. Never leak native file/VFS/journal pointers,
  * change chunk size, execute native PRAGMA, or allocate via SIZE_HINT. */
 if(op==1) return M(f)->control(R(f),op,a);
 if(op>=31&&op<=33){if(failed())return IOERR;return M(f)->control(R(f),op,a);}
 if(op==18) {if(a) *(I64*)a=0;return OK;} /* MMAP_SIZE: no mapped DB pages */
 return NOTFOUND;
}
static int sector_file(File*f){return M(f)->sector(R(f));}
static int device_file(File*f){return M(f)->device(R(f));}
static int shmmap_file(File*f,int page,int size,int extend,void volatile**out){
 if(failed())return IOERR;
 if(page<0||size<=0||(I64)page+1>cap/size){fail(3);return FULL;}
 pthread_mutex_lock(&mutex);
 if(!inode_ok(paths[3])){if(!fault)fault=3;pthread_mutex_unlock(&mutex);return IOERR;}
 int rc=M(f)->shmmap(R(f),page,size,extend,out);
 if(rc==OK && *out && !g(f)->mapped){g(f)->mapped=1;maps++;}
 pthread_mutex_unlock(&mutex);
 return rc;
}
static int shmlock_file(File*f,int a,int n,int flags){return M(f)->shmlock(R(f),a,n,flags);}
static void shmbarrier_file(File*f){M(f)->shmbarrier(R(f));}
static int shmunmap_file(File*f,int remove){
 pthread_mutex_lock(&mutex);int others=maps-g(f)->mapped;
 if(remove&&others){if(!fault)fault=4;pthread_mutex_unlock(&mutex);return IOERR;}
 int rc=M(f)->shmunmap(R(f),remove);
 if(rc==OK&&g(f)->mapped){g(f)->mapped=0;maps--;}
 pthread_mutex_unlock(&mutex);return rc;
}
static int fetch_file(File*f,I64 o,int n,void**out){(void)f;(void)o;(void)n;*out=NULL;return OK;}
static int unfetch_file(File*f,I64 o,void*p){(void)f;(void)o;return p?fail(5):OK;}
static const Methods methods={3,close_file,read_file,write_file,truncate_file,sync_file,size_file,
 lock_file,unlock_file,reserved_file,control_file,sector_file,device_file,shmmap_file,
 shmlock_file,shmbarrier_file,shmunmap_file,fetch_file,unfetch_file};
static int open_file(Vfs*v,const char*name,File*out,int flags,int*used){
 (void)v; GuardFile *p=g(out); memset(p,0,sizeof(*p)); int s=slot(name);
 if(failed())return IOERR;
 pthread_mutex_lock(&mutex);
 if(s<0||!inode_ok(name)){if(!fault)fault=1;pthread_mutex_unlock(&mutex);return IOERR;}
 p->real=calloc(1,(size_t)base->szOsFile); if(!p->real){pthread_mutex_unlock(&mutex);return CANTOPEN;}
 int rc=base->open(base,name,p->real,flags,used);
 if(rc!=OK){if(p->real->pMethods)p->real->pMethods->close(p->real);free(p->real);p->real=NULL;
   if(!fault)fault=9;pthread_mutex_unlock(&mutex);return rc;}
 if(!p->real->pMethods||p->real->pMethods->iVersion!=3){
   if(p->real->pMethods)p->real->pMethods->close(p->real);free(p->real);p->real=NULL;
   if(!fault)fault=6;pthread_mutex_unlock(&mutex);return IOERR;}
 p->slot=s;handles[s]++;pthread_mutex_unlock(&mutex);
 p->file.pMethods=&methods;return OK;
}
static int delete_file(Vfs*v,const char*n,int d){(void)v;int s=slot(n);if(s<0)return fail(1);
 if(failed())return IOERR;
 pthread_mutex_lock(&mutex);int busy=handles[s]||(s==3&&maps);
 if(busy||!inode_ok(n)){if(!fault)fault=4;pthread_mutex_unlock(&mutex);return IOERR;}
 int rc=base->del(base,n,d);pthread_mutex_unlock(&mutex);return rc;}
static int access_file(Vfs*v,const char*n,int a,int*r){(void)v;if(slot(n)<0)return fail(1);return base->access(base,n,a,r);}
static int full_file(Vfs*v,const char*n,int z,char*out){(void)v;int rc=base->full(base,n,z,out);
 if(rc!=OK)return rc;return slot(out)==0?OK:fail(1);}
static void *no_dlopen(Vfs*v,const char*p){(void)v;(void)p;fail(7);return NULL;}
static int random_vfs(Vfs*v,int n,char*p){(void)v;return base->random(base,n,p);}
static int sleep_vfs(Vfs*v,int n){(void)v;return base->sleep(base,n);}
static int now_vfs(Vfs*v,double*p){(void)v;return base->now(base,p);}
static int error_vfs(Vfs*v,int n,char*p){(void)v;return base->error(base,n,p);}
static int now64_vfs(Vfs*v,I64*p){(void)v;return base->now64(base,p);}
int g0_install(void *original, int(*register_vfs)(Vfs*,int), const char*database, I64 limit){
 if(base||!original||!database||database[0]!='/'||strlen(database)>4000||limit<=0)return 1;
 Vfs *b=(Vfs*)original;
 if(b->iVersion!=3||strcmp(b->zName,"unix")||b->szOsFile<=0||b->szOsFile>65536)return 2;
 strcpy(paths[0],database);strcpy(paths[1],database);strcat(paths[1],"-journal");
 strcpy(paths[2],database);strcat(paths[2],"-wal");strcpy(paths[3],database);strcat(paths[3],"-shm");
 base=b;cap=limit;proxy=*base;proxy.pNext=NULL;proxy.zName="sim2act_g0_bounded";
 proxy.szOsFile=(int)sizeof(GuardFile);proxy.open=open_file;proxy.del=delete_file;
 proxy.access=access_file;proxy.full=full_file;proxy.dlopen=no_dlopen;
 proxy.random=random_vfs;proxy.sleep=sleep_vfs;proxy.now=now_vfs;proxy.error=error_vfs;proxy.now64=now64_vfs;
 proxy.setsys=NULL;proxy.getsys=NULL;proxy.nextsys=NULL;
 return register_vfs(&proxy,1);
}
int g0_fault(void){pthread_mutex_lock(&mutex);int f=fault;pthread_mutex_unlock(&mutex);return f;}
int g0_open_handles(void){pthread_mutex_lock(&mutex);int n=maps;for(int i=0;i<4;i++)n+=handles[i];pthread_mutex_unlock(&mutex);return n;}
