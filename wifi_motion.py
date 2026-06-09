#!/usr/bin/env python3
"""
Detector de movimento por RSSI usando WiFi comum.
Mede a flutuacao do sinal do roteador: parado = estavel, movimento = instavel.

Uso:
    python3 wifi_motion.py                 # calibra 10s e detecta 60s
    python3 wifi_motion.py --calib 15 --run 120
    python3 wifi_motion.py --gw 192.168.1.1
"""
import argparse, subprocess, time, statistics, sys, os, signal, re

def find_iface():
    try:
        with open("/proc/net/wireless") as f:
            for line in f.readlines()[2:]:
                name = line.split(":")[0].strip()
                if name:
                    return name
    except FileNotFoundError:
        pass
    return None

def read_rssi(iface):
    """Le o nivel do sinal (dBm) em /proc/net/wireless."""
    try:
        with open("/proc/net/wireless") as f:
            for line in f:
                if line.strip().startswith(iface + ":"):
                    # campos: status link level noise ...
                    parts = line.split()
                    level = parts[3]            # ex: -57.
                    return float(level.rstrip("."))
    except Exception:
        return None
    return None

def default_gw():
    try:
        out = subprocess.check_output(["ip", "route"], text=True)
        m = re.search(r"default via (\S+)", out)
        return m.group(1) if m else None
    except Exception:
        return None

def bar(value, vmax, width=30):
    n = int(min(value / vmax, 1.0) * width) if vmax > 0 else 0
    return "#" * n + "-" * (width - n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calib", type=float, default=10.0, help="segundos de calibracao (ambiente parado)")
    ap.add_argument("--run", type=float, default=60.0, help="segundos de deteccao")
    ap.add_argument("--gw", default=None, help="IP do roteador (para o ping de refresh)")
    ap.add_argument("--interval", type=float, default=0.15, help="intervalo de amostragem (s)")
    ap.add_argument("--sens", type=float, default=2.5, help="sensibilidade (menor = mais sensivel)")
    args = ap.parse_args()

    iface = find_iface()
    if not iface:
        print("ERRO: nenhuma interface WiFi encontrada em /proc/net/wireless.")
        sys.exit(1)
    gw = args.gw or default_gw()

    print(f"Interface : {iface}")
    print(f"Roteador  : {gw or '(sem ping de refresh)'}")
    print(f"Amostragem: {1/args.interval:.0f} leituras/seg\n")

    # ping leve em segundo plano para forcar refresh do RSSI (0.2s nao exige root)
    ping_proc = None
    if gw:
        ping_proc = subprocess.Popen(
            ["ping", "-i", "0.2", "-q", gw],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def cleanup(*_):
        if ping_proc:
            ping_proc.terminate()
        print("\nEncerrado.")
        sys.exit(0)
    signal.signal(signal.SIGINT, cleanup)

    win = max(5, int(1.0 / args.interval))  # janela ~1s para o desvio padrao

    # ---- CALIBRACAO ----
    print(f">>> CALIBRANDO {args.calib:.0f}s — FIQUE PARADO / saia do comodo <<<")
    calib_samples = []
    t_end = time.time() + args.calib
    last = None
    while time.time() < t_end:
        r = read_rssi(iface)
        if r is not None:
            calib_samples.append(r)
            last = r
        time.sleep(args.interval)

    if len(calib_samples) < win:
        print("ERRO: poucas amostras. O sinal pode nao estar atualizando.")
        cleanup()

    # desvio padrao das janelas durante a calibracao = "ruido de base"
    base_devs = []
    for i in range(win, len(calib_samples)):
        base_devs.append(statistics.pstdev(calib_samples[i-win:i]))
    base = statistics.median(base_devs) if base_devs else 0.0
    base_mean = statistics.mean(calib_samples)
    threshold = max(base * args.sens, base + 1.0)

    print(f"Sinal medio    : {base_mean:.1f} dBm")
    print(f"Ruido de base  : {base:.2f}")
    print(f"Limite alarme  : {threshold:.2f}\n")
    print(f">>> DETECTANDO {args.run:.0f}s — ande pelo comodo para testar <<<\n")

    # ---- DETECCAO ----
    buf = list(calib_samples[-win:])
    t_end = time.time() + args.run
    detections = 0
    vmax = threshold * 2.5
    while time.time() < t_end:
        r = read_rssi(iface)
        if r is not None:
            buf.append(r)
            if len(buf) > win:
                buf.pop(0)
        dev = statistics.pstdev(buf) if len(buf) >= 2 else 0.0
        moving = dev > threshold
        if moving:
            detections += 1
        tag = "  *** MOVIMENTO ***" if moving else ""
        sys.stdout.write(f"\r[{bar(dev, vmax)}] var={dev:5.2f} (limite {threshold:.2f}){tag}        ")
        sys.stdout.flush()
        time.sleep(args.interval)

    print(f"\n\nFim. Amostras com movimento: {detections}")
    cleanup()

if __name__ == "__main__":
    main()
