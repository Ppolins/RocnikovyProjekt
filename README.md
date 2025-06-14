## O projekte

Tento program slúži na automatické overenie správnosti SQL dotazov študentov. Najskôr vytvorí SQLite databázu na základe
definície tabuliek – buď s fixnými (stabilnými), alebo náhodne generovanými údajmi. Následne spustí všetky SQL dotazy študentov
zo zadaného priečinka a pre každý dotaz zistí jeho výsledok. Výsledky sú navzájom porovnané a väčšinový výsledok je považovaný
za správny. Každý dotaz, ktorý sa s týmto výsledkom nezhoduje, je označený ako nesprávny (`FAIL`). Program taktiež sleduje čas
vykonávania každého dotazu – ak vykonanie prekročí stanovený časový limit (napr. kvôli nekonečnému cyklu), dotaz sa preruší a
výsledok sa označí ako `TLE`. Voliteľne je možné zapnúť AI spätnú väzbu, ktorá pre nesprávne dotazy automaticky vygeneruje komentár
pomocou modelu Gemini. Výsledky hodnotenia študentov sú nakoniec zapísané do CSV súboru `results.csv`.

## Ciele projektu

- Porovnať výsledky SQL dotazov medzi študentmi.
- Identifikovať väčšinový správny výstup.
- Označiť každého študenta ako `OK` / `FAIL` / `ERROR`.
- Poskytnúť spätnú väzbu pomocou AI modelu (Google Gemini).

## Požiadavky na vstup a výstup

### Vstup

Program potrebuje nasledovné súbory:

- **`createTables.txt`**  
  Textový súbor s popisom tabuliek, ktoré sa vytvoria v SQLite databáze. Je vo formáte slovníka Pythonu – každá tabuľka má svoj názov a zoznam
  stĺpcov vrátane prípadných `FOREIGN KEY` obmedzení. Tento súbor sa nachádza predvolene na ceste `data/createTables/createTables.txt`.

- **SQL dotazy študentov**  
  Každý študent má svoj `.sql` súbor s dotazom. Tieto súbory sa ukladajú do priečinka, napríklad `data/students/`.
  Meno súboru (bez `.sql`) sa považuje za meno študenta.

### Výstup

- **`results.csv`**  
  CSV súbor s dvoma stĺpcami:
  - Meno študenta
  - Výsledok (`OK`, `FAIL`, `TLE`, alebo `ERROR`)

  Tento súbor obsahuje zhrnutie výsledkov hodnotenia SQL dotazov. Výsledky sa tiež zobrazujú na konzole počas behu programu. V prípade zapnutej AI
  spätnej väzby sa zobrazí aj komentár ku každému dotazu, ktorý bol označený ako `FAIL`.

## Závislosti

Pred spustením projektu je potrebné mať nainštalované nasledovné knižnice:

```bash
pip install google-generativeai python-dotenv
pip install pytest
```

## Inštalácia

### Získanie Gemini API kľúča

1. Navštív stránku: [https://ai.google.dev/](https://ai.google.dev/)
2. Prihlás sa so svojím Google účtom.
3. Klikni na „Get API key“ alebo choď priamo na: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
4. Skopíruj svoj kľúč.
5. V koreňovom priečinku projektu vytvor súbor `.env` a vlož doň:
GEMINI_API_KEY=sk-...tvoj-kľúč...

### Spustenie programu

V termináli v koreňovom priečinku projektu spusti:

```bash
python3 main.py
```

### Voliteľné argumenty

- `--students` cesta k priečinku s SQL dotazmi (default: `data/students`)
- `--tables` cesta k definícii tabuliek (default: `data/createTables/createTables.txt`)
- `--output` názov CSV súboru pre výstup (default: `results.csv`)
- `--timeout` časový limit v sekundách pre dotazy (default: 3)
- `--random-db` ak je zadané, použije sa náhodná databáza

### Príklad:

```bash
python3 main.py --random-db --timeout 5
```

## Testovanie

Na spustenie testov (ak používaš pytest):

```bash
python3 -m pytest -v test_main.py
```
