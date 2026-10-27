# -*- coding: utf-8 -*-
"""와인호외 릴스용 배경음악 — 저작권 없는 자작곡을 그 자리에서 합성한다.

  python3 mk_music.py <출력.wav> [--sec 18] [--mood warm|brisk] [--seed 7]

  뮤직박스 풍 아르페지오 + 낮은 패드 + 레코드 잡음. 단조, 느린 왈츠 느낌.
"""
import argparse, math, numpy as np, wave, random

SR = 48000

def note(freq, dur, t0, out, amp=0.22, decay=2.6, harm=(1.0, 0.35, 0.12)):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.exp(-t * decay) * (1 - np.exp(-t * 400))        # 빠른 어택, 지수 감쇠
    sig = sum(a * np.sin(2*np.pi*freq*(k+1)*t) for k, a in enumerate(harm))
    i0 = int(t0 * SR); i1 = min(len(out), i0 + n)
    out[i0:i1] += (amp * env * sig)[:i1-i0]

def pad(freqs, dur, t0, out, amp=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.minimum(1, t/1.2) * np.minimum(1, (dur - t)/1.5)
    sig = sum(np.sin(2*np.pi*f*t) * 0.6 + 0.4*np.sign(np.sin(2*np.pi*f*t))*0.15 for f in freqs)
    i0 = int(t0 * SR); i1 = min(len(out), i0 + n)
    out[i0:i1] += (amp * env * sig)[:i1-i0]

def lowpass(x, cutoff=2600.0):
    rc = 1/(2*math.pi*cutoff); a = (1/SR)/(rc + 1/SR)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y

def reverb(x, delay=0.21, fb=0.42, mix=0.28):
    d = int(delay*SR); y = x.copy()
    for i in range(d, len(x)):
        y[i] += fb * y[i-d]
    return (1-mix)*x + mix*y

NOTES = {'A3':220.0,'C4':261.63,'D4':293.66,'E4':329.63,'F4':349.23,'G4':392.0,'A4':440.0,
         'C5':523.25,'D5':587.33,'E5':659.25,'F5':698.46,'G5':783.99,'A5':880.0,
         'F3':174.61,'G3':196.0,'D3':146.83,'E3':164.81,'C3':130.81,'B3':246.94,'B4':493.88}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--sec', type=float, default=18)
    ap.add_argument('--mood', default='warm'); ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    total = a.sec; out = np.zeros(int(total*SR) + SR)
    bpm = 72 if a.mood == 'warm' else 92
    beat = 60/bpm; bar = beat*3                       # 3/4
    # 코드 진행 (Am 조성) — 화음마다 아르페지오 패턴
    prog = [('Am',['A3','C4','E4','A4']),('F',['F3','A3','C4','F4']),('C',['C4','E4','G4','C5']),('G',['G3','B3','D4','G4']),
            ('Am',['A3','C4','E4','A4']),('F',['F3','A3','C4','F4']),('Dm',['D4','F4','A4','D5']),('E',['E3','B3','E4','G4'])]
    padmap = {'Am':['A3','E4'],'F':['F3','C4'],'C':['C4','G4'],'G':['G3','D4'],'Dm':['D3','A3'],'E':['E3','B3']}
    t = 0.0; ci = 0
    while t < total - 0.5:
        name, arp = prog[ci % len(prog)]; ci += 1
        pad([NOTES[n]/2 for n in padmap[name]], bar, t, out, amp=0.045)
        # 왈츠: 1박 베이스, 2·3박 상성 아르페지오 (8분음표)
        note(NOTES[arp[0]]/2, 1.6, t, out, amp=0.20, decay=2.0)
        pattern = [1,2,3,2,1,3] if a.mood=='warm' else [1,3,2,3,1,2]
        for k in range(6):
            tt = t + beat*0.5*(k+1)*1.0
            if tt < t + bar:
                idx = pattern[k]
                f = NOTES[arp[idx]] * (2 if rnd.random() < 0.18 else 1)
                note(f, 1.4, tt, out, amp=0.16 + 0.04*rnd.random(), decay=2.8)
        t += bar
    out = lowpass(out, 3200)
    out = reverb(out)
    # 레코드 잡음
    crackle = np.zeros_like(out)
    for _ in range(int(total*9)):
        i = rnd.randrange(len(out)-50); crackle[i:i+rnd.randrange(3,30)] += rnd.uniform(-0.03,0.03)
    noise = np.random.default_rng(a.seed).normal(0, 0.0025, len(out))
    out = out + lowpass(crackle + noise, 1800)
    # 페이드
    n = len(out); fi = int(0.8*SR); fo = int(1.8*SR); end = int(total*SR)
    out[:fi] *= np.linspace(0,1,fi); out[end-fo:end] *= np.linspace(1,0,fo); out[end:] = 0
    out = out[:end]
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.5          # 피크 -6 dBFS
    data = (out * 32767).astype(np.int16)
    with wave.open(a.out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
    print(f'{a.out}  {total:.1f}초  {bpm}bpm  {a.mood}')

if __name__ == '__main__':
    main()
