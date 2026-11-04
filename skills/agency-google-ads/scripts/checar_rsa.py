"""Confere limites de anúncios responsivos (RSA) do Google Ads.

Uso:
    python checar_rsa.py rsa.txt

O arquivo pode ter vários RSAs. Linhas que começam com "T:" são títulos (máx. 30),
"D:" descrições (máx. 90), "P:" caminhos (máx. 15), "S:" sitelink (título máx. 25),
"C:" frases de destaque (máx. 25). Uma linha começando com "RSA" inicia um novo anúncio.
Exemplo:
    RSA1 GA1
    T: Waterfall Dining Tables
    D: Carved from a single tree. 7 to 12 ft, one launch price of $6,600.
"""
import sys

LIMITES = {"T": 30, "D": 90, "P": 15, "S": 25, "C": 25}
NOMES = {"T": "título", "D": "descrição", "P": "caminho", "S": "sitelink", "C": "destaque"}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    ads, atual, erros = [], None, 0
    for n, linha in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
        linha = linha.rstrip("\n")
        if linha.upper().startswith("RSA"):
            atual = {"nome": linha.strip(), "T": [], "D": []}
            ads.append(atual)
            continue
        if len(linha) > 2 and linha[1] == ":" and linha[0].upper() in LIMITES:
            k, txt = linha[0].upper(), linha[2:].strip()
            tam = len(txt)
            ok = tam <= LIMITES[k]
            if not ok:
                erros += 1
            print(f"{'OK ' if ok else 'ERRO'} L{n} {NOMES[k]:9} {tam:3}/{LIMITES[k]}  {txt}")
            if atual is not None and k in ("T", "D"):
                atual[k].append(txt)
    for a in ads:
        t, d = len(a["T"]), len(a["D"])
        dup = len(a["T"]) - len({x.lower() for x in a["T"]})
        status = "OK" if t == 15 and d == 4 and not dup else "REVISAR"
        if status != "OK":
            erros += 1
        print(f"{status}: {a['nome']} — {t}/15 títulos, {d}/4 descrições" + (f", {dup} título(s) repetido(s)" if dup else ""))
    print("Tudo dentro dos limites." if not erros else f"{erros} problema(s) para corrigir antes de entregar.")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
