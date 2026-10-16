/* Bounded UTF8 lexical transport. Ru owns vocabulary and all structural folds.
 * No Scintilla, OS callbacks, document handles, retained pointers or allocation. */
#include "ru_scan.h"
#include <string.h>
#include "ru_unicode_data.h"
#define CONFIG_MAGIC 0x52554346u
#define STATE_MAGIC 0x52555354u
#define M_NORMAL 0u
#define M_NAME 1u
#define M_NUMBER 2u
#define M_LINE 3u
#define M_BLOCK 4u
#define M_STRING 5u
typedef struct Entry { uint8_t length,tag,style,reserved; uint8_t text[64]; } Entry;
typedef struct Config { uint32_t magic,count; Entry entries[RU_SCAN_CONFIG_LIMIT]; } Config;
typedef struct State {
    uint32_t magic,offset,line,mode,quote,escaped,previous_alnum,previous_cr;
    uint32_t number_phase,name_start,name_line,name_scalars,prefix_length;
    uint32_t carry_length,done,reserved;
    uint8_t prefix[64],carry[16];
} State;
typedef char StateLayoutMustBe144[(sizeof(State)==144)?1:-1];
typedef char EventLayoutMustBe16[(sizeof(RuScanEvent)==16)?1:-1];
typedef char ResultLayoutMustBe40[(sizeof(RuScanResult)==40)?1:-1];
static int decode(const uint8_t *p,uint32_t n,uint32_t *cp) {
    uint32_t c,min,k,i;
    if(!n)return 0;
    if(p[0]<0x80){if(!p[0])return -1;*cp=p[0];return 1;}
    if(p[0]>=0xc2&&p[0]<=0xdf){c=p[0]&31u;k=2;min=0x80;}
    else if(p[0]>=0xe0&&p[0]<=0xef){c=p[0]&15u;k=3;min=0x800;}
    else if(p[0]>=0xf0&&p[0]<=0xf4){c=p[0]&7u;k=4;min=0x10000;}
    else return -1;
    for(i=1;i<k&&i<n;i++){if((p[i]&0xc0)!=0x80)return -1;c=(c<<6)|(p[i]&63u);}
    if(n<k){
        if(n>1&&((p[0]==0xe0&&p[1]<0xa0)||(p[0]==0xed&&p[1]>=0xa0)||
                 (p[0]==0xf0&&p[1]<0x90)||(p[0]==0xf4&&p[1]>=0x90)))return -1;
        return 0;
    }
    if(c<min||c>0x10ffff||(c>=0xd800&&c<=0xdfff))return -1;
    *cp=c;return (int)k;
}
static int in_ranges(uint32_t cp,const uint32_t (*ranges)[2],size_t count){
    size_t lo=0,hi=count;
    while(lo<hi){size_t mid=lo+(hi-lo)/2;if(cp<ranges[mid][0])hi=mid;
        else if(cp>ranges[mid][1])lo=mid+1;else return 1;}return 0;
}
static int alpha(uint32_t c){
    if(c=='_')return 1;
    if(c<128)return(c>='A'&&c<='Z')||(c>='a'&&c<='z');
    return in_ranges(c,ru_alpha_ranges,sizeof(ru_alpha_ranges)/sizeof(ru_alpha_ranges[0]));
}
static int alnum(uint32_t c){
    if(c=='_')return 1;
    if(c<128)return(c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9');
    return in_ranges(c,ru_alnum_ranges,sizeof(ru_alnum_ranges)/sizeof(ru_alnum_ranges[0]));
}
static int digit(uint32_t c){return c>='0'&&c<='9';}
static int space(uint32_t c){return(c>=9&&c<=13)||(c>=28&&c<=32)||c==0x85||c==0xa0||
    c==0x1680||(c>=0x2000&&c<=0x200a)||c==0x2028||c==0x2029||c==0x202f||c==0x205f||c==0x3000;}
static uint32_t punctuation(uint32_t c){
    switch(c){case 0x3002:return '.';case 0xff1a:return ':';case 0xff08:return '(';
      case 0xff09:return ')';case 0xff0c:return ',';case 0xff3b:return '[';
      case 0xff3d:return ']';case 0xff5b:return '{';case 0xff5d:return '}';default:break;}
    if(c<128&&strchr(".:(),[]{}@+-*/%<>=!",(int)c))return c;
    return 0;
}
static const Entry *lookup(const Config *cfg,const uint8_t *text,uint32_t length){
    uint32_t i;
    for(i=0;i<cfg->count;i++){
        if(cfg->entries[i].length==length&&!memcmp(cfg->entries[i].text,text,length))return &cfg->entries[i];
    }
    return NULL;
}
static void event(RuScanEvent *events,uint32_t *count,uint32_t kind,uint32_t tag,
                  uint32_t style,uint32_t start,uint32_t length,uint32_t line){
    events[*count].head=(uint64_t)kind|((uint64_t)tag<<8)|((uint64_t)style<<16)|((uint64_t)start<<24);
    events[*count].tail=(uint64_t)length|((uint64_t)line<<32);++*count;
}
static void consume(State *s,uint32_t cp,uint32_t width,uint8_t style,uint8_t *styles,
                    uint32_t *i,RuScanEvent *events,uint32_t *count){
    memset(styles+*i,style,width);
    if(cp=='\r'||(cp=='\n'&&!s->previous_cr)){
        event(events,count,RU_EVENT_EOL,0,0,s->offset,width,s->line);++s->line;
    }
    s->previous_cr=cp=='\r';s->previous_alnum=(uint32_t)alnum(cp);
    s->offset+=width;*i+=width;
}
static void finish_name(const Config *cfg,State *s,RuScanEvent *events,uint32_t *count){
    const Entry *entry=s->name_scalars<=16?lookup(cfg,s->prefix,s->prefix_length):NULL;
    event(events,count,RU_EVENT_NAME,entry?entry->tag:0,entry?entry->style:8,
          s->name_start,s->offset-s->name_start,s->name_line);
    s->mode=M_NORMAL;s->prefix_length=0;s->name_scalars=0;s->name_start=0;s->name_line=0;memset(s->prefix,0,sizeof(s->prefix));
}
RU_SCAN_API uint32_t ru_scan_abi(void){return RU_SCAN_ABI;}
RU_SCAN_API uint32_t ru_scan_config_size(void){return (uint32_t)sizeof(Config);}
RU_SCAN_API uint32_t ru_scan_state_size(void){return (uint32_t)sizeof(State);}
static int decimal(const char *text,uint32_t length,uint32_t *at,uint8_t *out){
    uint32_t n=0,begin=*at;while(*at<length&&text[*at]>='0'&&text[*at]<='9'){
        n=n*10u+(uint32_t)(text[*at]-'0');if(n>255)return 0;++*at;}
    if(*at==begin||*at>=length||text[*at]!=':')return 0;
    ++*at;*out=(uint8_t)n;return 1;
}
RU_SCAN_API uint32_t ru_scan_config_init(void *memory,uint32_t size,const char *words,uint32_t length){
    Config cfg;uint32_t at=0;
    if(!memory||size<sizeof(Config)||(!words&&length)||length>65536)return RU_SCAN_BAD_ARGUMENT;
    memset(&cfg,0,sizeof(cfg));
    while(at<length){Entry *entry;uint32_t start,pos,cp,scalars=0;int width;
        if(cfg.count>=RU_SCAN_CONFIG_LIMIT)return RU_SCAN_BAD_ARGUMENT;
        entry=&cfg.entries[cfg.count];
        if(!decimal(words,length,&at,&entry->tag)||!decimal(words,length,&at,&entry->style))return RU_SCAN_BAD_ARGUMENT;
        start=at;while(at<length&&words[at]!='\n')++at;
        if(at==start||at-start>64)return RU_SCAN_BAD_ARGUMENT;
        entry->length=(uint8_t)(at-start);
        if(lookup(&cfg,(const uint8_t*)words+start,entry->length))return RU_SCAN_BAD_ARGUMENT;
        pos=start;while(pos<at){width=decode((const uint8_t*)words+pos,at-pos,&cp);if(width<=0||++scalars>16)return RU_SCAN_BAD_ARGUMENT;pos+=(uint32_t)width;}
        memcpy(entry->text,words+start,entry->length);++cfg.count;if(at<length)++at;
    }
    cfg.magic=CONFIG_MAGIC;memcpy(memory,&cfg,sizeof(cfg));return RU_SCAN_OK;
}
RU_SCAN_API uint32_t ru_scan_state_init(void *memory,uint32_t size){
    State s;if(!memory||size<sizeof(s))return RU_SCAN_BAD_ARGUMENT;memset(&s,0,sizeof(s));s.magic=STATE_MAGIC;memcpy(memory,&s,sizeof(s));return RU_SCAN_OK;
}
RU_SCAN_API uint32_t ru_scan_state_copy(void *target,const void *source,uint32_t size){
    const State *s=(const State*)source;
    if(!target||!s||size<sizeof(State)||s->magic!=STATE_MAGIC)return RU_SCAN_BAD_ARGUMENT;
    memmove(target,source,sizeof(State));return RU_SCAN_OK;
}
RU_SCAN_API uint32_t ru_scan_state_equal(const void *left,const void *right){
    const State *a=(const State*)left,*b=(const State*)right;
    return a&&b&&a->magic==STATE_MAGIC&&b->magic==STATE_MAGIC&&!memcmp(a,b,sizeof(State));
}
RU_SCAN_API uint32_t ru_scan_feed(const void *config,void *state,const uint8_t *input,
    uint32_t length,uint32_t input_offset,uint32_t eof,uint8_t *styles,uint32_t styles_capacity,
    RuScanEvent *events,uint32_t events_capacity,RuScanResult *result){
    const Config *cfg=(const Config*)config;State s;uint8_t data[RU_SCAN_MAX_STYLES];
    uint32_t old_carry,total,i=0,count=0,hold=0,status=RU_SCAN_OK,available,cp,check;
    if(!result)return RU_SCAN_BAD_ARGUMENT;
    memset(result,0,sizeof(*result));
#define FAIL(code) do{memset(result,0,sizeof(*result));result->status=(code);return(code);}while(0)
    if(!cfg||!state||!styles||!events||(!input&&length)||length>RU_SCAN_MAX_INPUT||input_offset>length||eof>1||events_capacity<8||events_capacity>64)FAIL(RU_SCAN_BAD_ARGUMENT);
    if(cfg->magic!=CONFIG_MAGIC||cfg->count>RU_SCAN_CONFIG_LIMIT)FAIL(RU_SCAN_BAD_STATE);
    memcpy(&s,state,sizeof(s));
    if(s.magic!=STATE_MAGIC||s.mode>M_STRING||s.carry_length>16||s.prefix_length>64||s.offset>32000000u||s.line>s.offset||s.name_start>s.offset||s.name_line>s.line||s.name_scalars>s.offset||s.escaped>1||s.number_phase>2||s.previous_alnum>1||s.previous_cr>1||s.done>1)FAIL(RU_SCAN_BAD_STATE);
    available=length-input_offset;
    if(styles_capacity<available+16u)FAIL(RU_SCAN_BAD_ARGUMENT);
    result->start=s.offset;
    if(s.done){if(available||!eof)FAIL(RU_SCAN_BAD_STATE);result->done=1;result->line=s.line;result->bytes=s.offset;return RU_SCAN_OK;}
    old_carry=s.carry_length;total=old_carry+available;
    memcpy(data,s.carry,old_carry);if(available)memcpy(data+old_carry,input+input_offset,available);
    /* Validate before committing any state; partial trailing scalar may wait. */
    check=0;while(check<total){int width=decode(data+check,total-check,&cp);
        if(width<0||(width==0&&eof))FAIL(RU_SCAN_INVALID_UTF8);
        if(!width)break;
        check+=(uint32_t)width;}
    while(i<total){uint32_t cps[4]={0,0,0,0},widths[4]={0,0,0,0},n=0,pos=i,c,after,style=0,take=1,op;
        if(count+8>events_capacity){status=RU_SCAN_OUTPUT_FULL;break;}
        while(n<4&&pos<total){int width=decode(data+pos,total-pos,&cps[n]);if(width<=0)break;widths[n]=(uint32_t)width;pos+=(uint32_t)width;++n;}
        if(!eof&&n<4){hold=total-i;if(hold>16)FAIL(RU_SCAN_BAD_STATE);break;}
        if(!n)FAIL(RU_SCAN_INVALID_UTF8);
        c=cps[0];after=cps[1];
        if(s.mode==M_NAME){
            if(alnum(c)){
                ++s.name_scalars;if(s.name_scalars<=16){if(s.prefix_length+widths[0]>64)FAIL(RU_SCAN_BAD_STATE);memcpy(s.prefix+s.prefix_length,data+i,widths[0]);s.prefix_length+=widths[0];}style=8;
            }else{finish_name(cfg,&s,events,&count);continue;}
        }else if(s.mode==M_NUMBER){
            if(digit(c))style=3;
            else if(c=='.'&&s.number_phase==0&&digit(after)){s.number_phase=1;style=3;}
            else if((c=='e'||c=='E')&&s.number_phase<2&&(digit(after)||((after=='+'||after=='-')&&digit(cps[2])))){
                s.number_phase=2;style=3;if(after=='+'||after=='-')take=2;
            }else{s.mode=M_NORMAL;continue;}
        }else if(s.mode==M_LINE){style=1;if(c=='\n'){s.mode=M_NORMAL;style=0;}}
        else if(s.mode==M_BLOCK){style=1;if(c==0x91ca&&(after=='.'||after==0x3002)){
            event(events,&count,RU_EVENT_BLOCK_CLOSE,0,1,s.offset,widths[0]+widths[1],s.line);s.mode=M_NORMAL;take=2;}}
        else if(s.mode==M_STRING){style=2;if(s.escaped){
            if(!(c=='n'||c=='r'||c=='t'||c=='\\'||c=='\''||c=='"'||c==0x2019||c==0x201d))style=9;
            s.escaped=0;
        }else if(c=='\\')s.escaped=1;else if(c==s.quote)s.mode=M_NORMAL;}
        else if(c=='#'||(c=='/'&&after=='/')||(c==0x6279&&(after=='.'||after==0x3002)&&!s.previous_alnum)){
            s.mode=M_LINE;style=1;if(c!='#')take=2;
        }else if(c==0x89e3&&(after=='.'||after==0x3002)&&!s.previous_alnum){
            event(events,&count,RU_EVENT_BLOCK_OPEN,0,1,s.offset,widths[0]+widths[1],s.line);s.mode=M_BLOCK;style=1;take=2;
        }else if(c=='\''||c=='"'||c==0x2018||c==0x201c){
            s.mode=M_STRING;s.quote=c==0x2018?0x2019:c==0x201c?0x201d:c;s.escaped=0;style=2;
            event(events,&count,RU_EVENT_STRING,0,2,s.offset,widths[0],s.line);
        }else if(digit(c)||(c=='.'&&digit(after))){
            s.mode=M_NUMBER;s.number_phase=c=='.';style=3;
            event(events,&count,RU_EVENT_NUMBER,0,3,s.offset,widths[0],s.line);
        }else if(alpha(c)){
            s.mode=M_NAME;s.name_start=s.offset;s.name_line=s.line;s.name_scalars=1;s.prefix_length=widths[0];
            memset(s.prefix,0,sizeof(s.prefix));memcpy(s.prefix,data+i,widths[0]);style=8;
        }else if(space(c)||(s.offset==0&&c==0xfeff))style=0;
        else if((op=punctuation(c))!=0){uint8_t spelling[2];const Entry *entry;uint32_t size=1;
            spelling[0]=(uint8_t)op;
            if(((c==':'||c==0xff1a)&&after=='=')||((c=='='||c=='!'||c=='<'||c=='>')&&after=='=')){
                spelling[1]='=';size=2;take=2;}
            entry=lookup(cfg,spelling,size);style=7;
            event(events,&count,RU_EVENT_OPERATOR,entry?entry->tag:0,7,s.offset,widths[0]+(take==2?widths[1]:0),s.line);
        }else style=9;
        consume(&s,c,widths[0],(uint8_t)style,styles,&i,events,&count);
        if(take==2)consume(&s,after,widths[1],(uint8_t)style,styles,&i,events,&count);
        if(s.offset>32000000u)FAIL(RU_SCAN_BAD_STATE);
    }
    memset(s.carry,0,sizeof(s.carry));s.carry_length=0;
    if(hold){memcpy(s.carry,data+i,hold);s.carry_length=hold;result->consumed=available;}
    else if(i<old_carry){s.carry_length=old_carry-i;memcpy(s.carry,data+i,s.carry_length);result->consumed=0;}
    else result->consumed=i-old_carry;
    if(eof&&i==total){
        if(s.mode==M_NAME){if(count<events_capacity)finish_name(cfg,&s,events,&count);else status=RU_SCAN_OUTPUT_FULL;}
        if(s.mode==M_NUMBER)s.mode=M_NORMAL;
        if(status!=RU_SCAN_OUTPUT_FULL)s.done=1;
    }
    if(s.mode!=M_NUMBER)s.number_phase=0;
    if(s.mode!=M_STRING){s.quote=0;s.escaped=0;}
    result->status=status;result->styled=i;result->events=count;result->line=s.line;result->done=s.done;result->bytes=s.offset;
    memcpy(state,&s,sizeof(s));return status;
#undef FAIL
}
