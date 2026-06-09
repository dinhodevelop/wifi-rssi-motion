# WiFi RSSI Motion Detector

Detector de movimento usando **WiFi comum** — sem câmera, sem hardware especial.
Mede a flutuação da força do sinal (RSSI) entre o seu PC e o roteador: ambiente
parado = sinal estável; alguém se movendo = sinal instável.

> ⚠️ **Leia a seção [Limitações](#limitações) antes de criar expectativas.**
> Isto é um **sensor de barreira** ("passou alguém"), **não** um radar que vê pose
> ou localiza pessoas. Para isso é preciso CSI, que WiFi comum não expõe.

## Como funciona

Toda vez que o PC recebe um pacote do roteador, o sistema registra a potência do
sinal (RSSI) em `/proc/net/wireless`. Quando uma pessoa se move entre o PC e o
roteador (ou perto deles), ela perturba os caminhos do sinal (multipath) e o RSSI
oscila mais que o normal.

O script:

1. **Calibra** o "ruído de base" com o ambiente parado.
2. **Monitora** o desvio padrão do sinal numa janela deslizante (~1s).
3. **Alarma** quando a variação ultrapassa o limite aprendido na calibração.

Para o RSSI atualizar rápido (ele só muda quando chegam pacotes), o script dispara
um `ping` leve no roteador em segundo plano (~5 pacotes/seg, banda desprezível).

## Requisitos

- Linux com interface WiFi (lê `/proc/net/wireless`)
- Python 3 (apenas biblioteca padrão — sem dependências)
- `ping` e `ip` disponíveis (padrão na maioria das distros)

## Uso

```bash
# Calibra 10s (fique parado) e detecta por 60s (ande para testar)
python3 wifi_motion.py

# Calibração e duração personalizadas
python3 wifi_motion.py --calib 15 --run 120

# Especificar o IP do roteador manualmente
python3 wifi_motion.py --gw 192.168.1.1
```

Durante a **calibração**, fique parado ou saia do cômodo. Durante a **detecção**,
ande, levante o braço, passe entre o PC e o roteador — a barra enche e aparece
`*** MOVIMENTO ***`.

### Opções

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `--calib` | 10 | Segundos de calibração (ambiente parado) |
| `--run` | 60 | Segundos de detecção |
| `--gw` | auto | IP do roteador (para o ping de refresh) |
| `--interval` | 0.15 | Intervalo de amostragem em segundos |
| `--sens` | 2.5 | Sensibilidade — **menor = mais sensível** |

### Calibrando a sensibilidade

| Situação | Ajuste |
|----------|--------|
| Acusa movimento à toa | aumente: `--sens 4` |
| Não detecta seu movimento | diminua: `--sens 1.8` |

## Validando se realmente funciona (teste de controle)

RSSI oscila sozinho. Para provar que o detector responde a movimento (e não a
ruído), compare dois cenários:

1. **Sala vazia** — saia do cômodo e rode. Anote "Amostras com movimento".
2. **Você andando** — rode e se movimente bastante. Anote o número.

Se o segundo for **muito maior** que o primeiro, está funcionando. Se forem
parecidos, aumente `--sens` ou aproxime o teste da linha PC↔roteador.

## Limitações

Isto usa **RSSI**, que é um único número por leitura. Por isso:

- ✅ Detecta **presença/movimento** ("tem alguém se mexendo")
- ❌ **Não** localiza onde a pessoa está (1 link = sem triangulação)
- ❌ **Não** estima pose, esqueleto, respiração ou batimentos
- ❌ **Não** "vê através da parede" como os vídeos virais

Os recursos avançados (pose, vitais, mapa) dependem de **CSI** (amplitude e fase
por subportadora), que roteadores comuns **não expõem**. Para CSI é preciso
hardware específico: **ESP32-S3**, NICs de pesquisa (Intel 5300 / Atheros AR9xxx),
ou roteadores com chipset suportado pelo OpenWRT + ferramenta de CSI.

## Aviso

Use apenas em redes e ambientes próprios. Detecção de movimento em espaços onde
há expectativa de privacidade pode ser ilegal dependendo da jurisdição.

## Licença

MIT
