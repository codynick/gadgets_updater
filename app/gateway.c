/* ATmega328P, 16 MHz. PC: 9600 8N1. Gadget: software UART 9600 8E1.
 * Application-only updater. Write/erase below 0x08000800 is rejected.
 * No global erase, protection changes, option writes or GO command.
 */
#define F_CPU 16000000UL
#include <avr/io.h>
#include <util/delay.h>
#include <stdint.h>

/* CJP v6 status: the original Lite binary configures 16 GRB/800 kHz pixels
 * on Arduino A2 (PC2). Pixel 0 is blue when idle, green after H succeeds.
 * Updates occur only between complete UART transactions, before PC response.
 * The serial protocol remains CJP5 for compatibility with the tested host.
 */
static uint8_t led_pixels[49]; /* 48 stream bytes plus one safe look-ahead byte */
static void status_led(uint8_t connected) {
    for(uint8_t i=0;i<48;i++)led_pixels[i]=0;
    led_pixels[0]=connected?10:0; /* GRB: green */
    led_pixels[2]=connected?0:10; /* blue; same brightness as original Lite */
    DDRC|=_BV(PC2);
    PORTC&=~_BV(PC2);
    _delay_us(300);
    uint8_t saved=SREG;
    __asm__ __volatile__("cli" ::: "memory");
    uint8_t hi=PORTC|_BV(PC2),lo=PORTC&~_BV(PC2);
    const uint8_t *ptr=led_pixels;
    uint8_t value=*ptr++,bits=8,next=lo;
    uint16_t count=48;
    /* Same 20-cycle, 16 MHz waveform used by Lite's 800 kHz routine.
     * Both bit paths and the byte boundary are exactly 20 CPU cycles.
     */
    __asm__ __volatile__(
        "1: st %a[port], %[hi]\n\t"
        "sbrc %[value], 7\n\t"
        "mov %[next], %[hi]\n\t"
        "dec %[bits]\n\t"
        "st %a[port], %[next]\n\t"
        "mov %[next], %[lo]\n\t"
        "breq 2f\n\t"
        "lsl %[value]\n\t"
        "rjmp .+0\n\t"
        "nop\n\t"
        "st %a[port], %[lo]\n\t"
        "nop\n\t"
        "rjmp .+0\n\t"
        "rjmp 1b\n\t"
        "2: ldi %[bits], 8\n\t"
        "ld %[value], %a[ptr]+\n\t"
        "st %a[port], %[lo]\n\t"
        "nop\n\t"
        "sbiw %[count], 1\n\t"
        "brne 1b\n\t"
        : [ptr] "+&x" (ptr), [value] "+&r" (value),
          [bits] "+&d" (bits), [next] "+&r" (next), [count] "+&w" (count)
        : [port] "z" (&PORTC), [hi] "r" (hi), [lo] "r" (lo)
        : "cc", "memory"
    );
    SREG=saved;
    _delay_us(300);
}

static void out(char c) { while (!(UCSR0A & _BV(UDRE0))) {} UDR0=c; }
static void msg(const char *s) { while (*s) out(*s++); }
static void num(uint16_t n) { char b[6]; uint8_t i=0; do { b[i++]='0'+n%10; n/=10; } while(n); while(i)out(b[--i]); }
static void hex(uint8_t n) { const char *h="0123456789ABCDEF"; out(h[n>>4]);out(h[n&15]); }
static uint8_t rx(void) { return !!(PINC & _BV(PC5)); }
static void tx(uint8_t v) { if(v)PORTC|=_BV(PC4);else PORTC&=~_BV(PC4); }
/* Timer1 ticks every 0.5 us. 208 ticks/bit = 9615 baud (0.16% high). */
static void until(uint16_t start,uint16_t ticks) {
    while((uint16_t)(TCNT1-start)<ticks){}
}
static void send_byte(uint8_t v) {
    uint8_t parity=0;
    uint16_t start=TCNT1;
    tx(0);
    for(uint8_t i=0;i<8;i++) {
        until(start,(uint16_t)(i+1)*208);
        uint8_t b=(v>>i)&1;tx(b);parity^=b;
    }
    until(start,1872);tx(parity);
    until(start,2080);tx(1);
    until(start,2288);
}
static uint8_t receive_byte(uint8_t *value,uint8_t *good,uint16_t timeout_ms) {
    uint32_t elapsed=0,limit=(uint32_t)timeout_ms*2000;
    uint16_t last=TCNT1;
    while(rx()) {
        uint16_t now=TCNT1;
        elapsed+=(uint16_t)(now-last);last=now;
        if(elapsed>=limit)return 0;
    }
    uint16_t start=TCNT1;
    uint8_t v=0,p=0;
    for(uint8_t i=0;i<8;i++) {
        until(start,312+(uint16_t)i*208);
        uint8_t b=rx();v|=b<<i;p^=b;
    }
    until(start,1976);uint8_t parity=rx();
    until(start,2184);uint8_t stop=rx();
    *value=v;*good=(parity==p && stop);
    return 1;
}
static uint8_t reply[64],reply_len,reply_good;
static void query(uint8_t command,const char *name) {
    /* Do not print while a reply is in progress. */
    reply_len=0;reply_good=1;
    send_byte(command);send_byte((uint8_t)~command);
    while(reply_len<sizeof(reply)) {
        uint8_t v,good;
        if(!receive_byte(&v,&good,reply_len?300:3000))break;
        reply[reply_len++]=v;reply_good&=good;
    }
    msg(name);msg(" RAW:");
    for(uint8_t i=0;i<reply_len;i++){out(' ');hex(reply[i]);}
    msg(" FRAME_OK=");num(reply_good && reply_len>0);msg("\r\n");
}
static uint8_t valid_reply(void) {
    return reply_good && reply_len>=4 && reply[0]==0x79 &&
        reply[reply_len-1]==0x79 && (uint16_t)reply[1]+4==reply_len;
}
static uint8_t ack(const char *stage) {
    uint8_t v=0,good=0;
    if(receive_byte(&v,&good,3000) && good && v==0x79)return 1;
    msg("READ_FAILED stage=");msg(stage);msg(" RX=");hex(v);
    msg(" FRAME_OK=");num(good);msg("\r\n");return 0;
}
static uint8_t read_once(uint32_t address,uint8_t count) {
    /* Read access limited by dispatcher to main flash. */
    if(!count || count>sizeof(reply))return 0;
    send_byte(0x11);send_byte(0xee);
    if(!ack("COMMAND"))return 0;
    uint8_t checksum=0;
    for(uint8_t i=0;i<4;i++) {
        uint8_t b=(uint8_t)(address>>(24-8*i));checksum^=b;send_byte(b);
    }
    send_byte(checksum);
    if(!ack("ADDRESS"))return 0;
    send_byte(count-1);send_byte((uint8_t)~(count-1));
    if(!ack("LENGTH"))return 0;
    uint8_t frames_good=1;
    for(uint8_t i=0;i<count;i++) {
        uint8_t good;
        if(!receive_byte(&reply[i],&good,1000)) {
            msg("READ_FAILED stage=DATA_TIMEOUT\r\n");return 0;
        }
        frames_good&=good;
    }
    if(!frames_good){msg("READ_FAILED stage=DATA_FRAME\r\n");return 0;}
    return 1;
}
static uint8_t flash_kb;
static uint8_t identify(void) {
    query(0x00,"GET");
    if(!valid_reply()) {msg("GET_INVALID; stopping\r\n");return 0;}
    msg("BOOTLOADER_VERSION_HEX=");hex(reply[2]);msg("\r\nSUPPORTED_COMMANDS:");
    uint8_t has_id=0,has_read=0,has_write=0,has_erase=0;
    for(uint8_t i=3;i<reply_len-1;i++) {
        out(' ');hex(reply[i]);if(reply[i]==0x02)has_id=1;
        if(reply[i]==0x11)has_read=1;
        if(reply[i]==0x31)has_write=1;
        if(reply[i]==0x44)has_erase=1;
    }
    msg("\r\n");
    if(!has_id){msg("GET_ID_NOT_ADVERTISED; stopping\r\n");return 0;}
    query(0x02,"GET_ID");
    if(!valid_reply()) {msg("GET_ID_INVALID; stopping\r\n");return 0;}
    msg("PRODUCT_ID_HEX=");
    for(uint8_t i=2;i<reply_len-1;i++)hex(reply[i]);
    msg("\r\nREAD_ONLY_IDENTIFICATION_COMPLETE\r\n");
    if(reply_len!=5 || reply[2]!=0x04 || reply[3]!=0x44) {
        msg("UNEXPECTED_PRODUCT_ID; memory checks skipped\r\n");return 0;
    }
    if(!has_read){msg("READ_NOT_ADVERTISED; stopping\r\n");return 0;}
    if(!(has_read && has_write && has_erase))return 0;
    if(!read_once(0x1ffff7ccUL,2))return 0;
    if(reply[1] || (reply[0]!=16 && reply[0]!=32))return 0;
    flash_kb=reply[0];msg("FLASH_SIZE_KB=");num(flash_kb);msg("\r\n");return 1;
}
static void wait_ms(uint16_t n) { while(n--)_delay_ms(1); }
static uint8_t handshake(void) {
    /* Startup directions: A5 output, A4 input with pull-up. */
    DDRC &= ~_BV(PC4); PORTC |= _BV(PC4);
    PORTC |= _BV(PC5); DDRC |= _BV(PC5);
    msg("CONNECT GADGET NOW; waiting up to 15 seconds\r\n");
    uint8_t previous=!!(PINC&_BV(PC4)), edges=0, found=0;
    uint16_t since=0, toggle=0, interval=0;
    for(uint16_t elapsed=0;elapsed<15000;elapsed++) {
        _delay_ms(1);since++;toggle++;
        if(toggle>=51) { PORTC^=_BV(PC5);toggle=0; }
        uint8_t current=!!(PINC&_BV(PC4));
        if(current!=previous) {
            edges++;interval=since;since=0;previous=current;
            if(edges>=2 && interval>=41 && interval<=59) {found=1;break;}
        }
    }
    /* Release startup output first. Programming directions reverse. */
    DDRC &= ~_BV(PC5);PORTC|=_BV(PC5);
    PORTC|=_BV(PC4);DDRC|=_BV(PC4);
    msg("RESPONSE_EDGES=");num(edges);msg(" LAST_INTERVAL_MS=");num(interval);msg("\r\n");
    if(!found) {msg("HANDSHAKE_NOT_CONFIRMED; no UART byte sent\r\n");return 0;}
    /* ROM entry follows the gadget's remaining 50 ms response pulses. */
    wait_ms(600);
    msg("HANDSHAKE_CONFIRMED; A5_IDLE=");num(rx());msg("\r\n");
    msg("Sending INIT 7F, gadget UART 9600 8E1\r\n");
    send_byte(0x7f);
    uint8_t value,good;
    if(receive_byte(&value,&good,3000)) {
        msg("INIT_RX=");hex(value);msg(" FRAME_OK=");num(good);msg("\r\n");
        if(value==0x79 && good)return identify();
        else msg("INIT_NOT_ACKNOWLEDGED; stopping\r\n");
    } else msg("INIT_TIMEOUT; no falling edge observed on A5\r\n");
    return 0;
}
/* Strict PC command protocol; CRC16 covers header and payload. */
static uint8_t payload[68],seq,command,ready;
static uint16_t crc_step(uint16_t crc,uint8_t b) {
    crc^=(uint16_t)b<<8;
    for(uint8_t i=0;i<8;i++)crc=(crc&0x8000)?(crc<<1)^0x1021:crc<<1;
    return crc;
}
static uint8_t pc_byte(uint8_t *b) {
    uint16_t last=TCNT1;uint32_t ticks=0;
    while(!(UCSR0A&_BV(RXC0))) {
        uint16_t now=TCNT1;ticks+=(uint16_t)(now-last);last=now;
        if(ticks>2000000UL)return 0;
    }
    uint8_t status=UCSR0A;*b=UDR0;
    return !(status&(_BV(FE0)|_BV(DOR0)|_BV(UPE0)));
}
static void response(uint8_t status,const uint8_t *data,uint8_t length) {
    uint16_t crc=0xffff;out(0x3c);out(0xa5);
    uint8_t header[4]={seq,command,status,length};
    for(uint8_t i=0;i<4;i++){out(header[i]);crc=crc_step(crc,header[i]);}
    for(uint8_t i=0;i<length;i++){out(data[i]);crc=crc_step(crc,data[i]);}
    out(crc>>8);out(crc);
}
static uint32_t address_of(const uint8_t *p) {
    return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint16_t)p[2]<<8|p[3];
}
static uint8_t allowed(uint32_t a,uint8_t n,uint8_t write) {
    uint32_t base=write?0x08000800UL:0x08000000UL;
    return flash_kb && n && n<=64 && a>=base && a<=0x08000000UL+(uint32_t)flash_kb*1024-n &&
           (!write || (!(a&3) && !(n&3)));
}
static uint8_t address_send(uint32_t a) {
    uint8_t sum=0;
    for(uint8_t i=0;i<4;i++){uint8_t v=a>>(24-8*i);send_byte(v);sum^=v;}
    send_byte(sum);return ack("ADDRESS");
}
static uint8_t erase_application_page(uint8_t page) {
    if(page<2 || page>=flash_kb)return 0;
    send_byte(0x44);send_byte(0xbb);
    if(!ack("ERASE_COMMAND"))return 0;
    /* Exactly one explicitly numbered page. No special/mass erase codes. */
    send_byte(0);send_byte(0);send_byte(0);send_byte(page);send_byte(page);
    uint8_t value,good;
    return receive_byte(&value,&good,15000) && good && value==0x79;
}
static uint8_t write_application(uint32_t address,uint8_t count) {
    if(!allowed(address,count,1))return 0;
    send_byte(0x31);send_byte(0xce);
    if(!ack("WRITE_COMMAND") || !address_send(address))return 0;
    uint8_t sum=count-1;send_byte(sum);
    for(uint8_t i=0;i<count;i++){uint8_t b=payload[4+i];send_byte(b);sum^=b;}
    send_byte(sum);
    if(!ack("WRITE_DATA") || !read_once(address,count))return 0;
    for(uint8_t i=0;i<count;i++)if(reply[i]!=payload[4+i])return 0;
    return 1;
}
static void dispatch(uint8_t length) {
    if(command=='P' && !length){response(0,(const uint8_t *)"CJP5",4);return;}
    if(command=='H' && !length){ready=0;flash_kb=0;status_led(0);ready=handshake();status_led(ready);response(ready?0:1,&flash_kb,1);return;}
    if(!ready){response(2,0,0);return;}
    if(command=='R' && length==5) {
        uint32_t a=address_of(payload);uint8_t n=payload[4];
        if(!allowed(a,n,0)){response(3,0,0);return;}
        if(read_once(a,n)){response(0,reply,n);return;}
    } else if(command=='E' && length==1) {
        if(payload[0]<2 || payload[0]>=flash_kb){response(3,0,0);return;}
        if(erase_application_page(payload[0])){response(0,payload,1);return;}
    } else if(command=='W' && length>=8 && length<=68) {
        uint32_t a=address_of(payload);uint8_t n=length-4;
        if(!allowed(a,n,1)){response(3,0,0);return;}
        if(write_application(a,n)){response(0,payload,4);return;}
    } else {response(3,0,0);return;}
    ready=0;status_led(0);response(1,0,0);
}
int main(void) {
    UCSR0A=0;UBRR0H=0;UBRR0L=103;
    UCSR0C=_BV(UCSZ01)|_BV(UCSZ00);UCSR0B=_BV(RXEN0)|_BV(TXEN0);
    TCCR1A=0;TCCR1B=_BV(CS11);TCNT1=0;
    DDRC&=~(_BV(PC4)|_BV(PC5));PORTC|=_BV(PC4)|_BV(PC5);
    status_led(0);
    msg("CJP APPLICATION TOOL v5; bootloader pages 0 and 1 excluded\r\n");
    for(;;) {
        uint8_t b,length,hi,lo;
        if(!pc_byte(&b) || b!=0xc3)continue;
        if(!pc_byte(&b) || b!=0x5a)continue;
        if(!pc_byte(&seq) || !pc_byte(&command) || !pc_byte(&length))continue;
        if(length>sizeof(payload)){ready=0;status_led(0);continue;}
        uint16_t crc=crc_step(crc_step(crc_step(0xffff,seq),command),length);
        uint8_t complete=1;
        for(uint8_t i=0;i<length;i++) {
            if(!pc_byte(&payload[i])){complete=0;break;}
            crc=crc_step(crc,payload[i]);
        }
        if(!complete || !pc_byte(&hi) || !pc_byte(&lo)){ready=0;status_led(0);continue;}
        if(crc!=((uint16_t)hi<<8|lo)){ready=0;status_led(0);response(4,0,0);continue;}
        dispatch(length);
    }
}
