import re

# PARSIRANJE

def tokeniziraj(tekst):
    uzorak = r"[A-Za-z][A-Za-z0-9_]*|[(),|~]"
    tokeni = re.findall(uzorak, tekst)

    if "".join(tokeni) != re.sub(r"\s+", "", tekst):
        raise ValueError("Neispravan znak u formuli.")

    return tokeni


class Parser:
    def __init__(self, tekst):
        self.tokeni = tokeniziraj(tekst)
        self.pozicija = 0

    def pogledaj(self):
        if self.pozicija >= len(self.tokeni):
            return None
        return self.tokeni[self.pozicija]

    def uzmi(self):
        token = self.pogledaj()

        if token is None:
            raise ValueError("Neočekivan kraj formule.")

        self.pozicija += 1
        return token

    def ocekuj(self, ocekivani):
        if self.uzmi() != ocekivani:
            raise ValueError("Neispravna sintaksa.")

    def parsiraj_termin(self):
        ime = self.uzmi()

        if not ime[0].isalpha():
            raise ValueError("Neispravan termin.")

        if self.pogledaj() == "(":
            self.uzmi()
            argumenti = []

            if self.pogledaj() != ")":
                argumenti.append(self.parsiraj_termin())

                while self.pogledaj() == ",":
                    self.uzmi()
                    argumenti.append(self.parsiraj_termin())

            self.ocekuj(")")

            return ("func", ime, argumenti)

        if ime[0].islower():
            return ("var", ime)

        return ("const", ime)

    def parsiraj_literal(self):
        negacija = False

        if self.pogledaj() == "~":
            self.uzmi()
            negacija = True

        predikat = self.uzmi()

        if not predikat[0].isupper():
            raise ValueError("Ime predikata mora počinjati velikim slovom.")

        self.ocekuj("(")
        argumenti = []

        if self.pogledaj() != ")":
            argumenti.append(self.parsiraj_termin())

            while self.pogledaj() == ",":
                self.uzmi()
                argumenti.append(self.parsiraj_termin())

        self.ocekuj(")")

        return (negacija, predikat, argumenti)

    def parsiraj_klauzulu(self):
        literali = [self.parsiraj_literal()]

        while self.pogledaj() == "|":
            self.uzmi()
            literali.append(self.parsiraj_literal())

        if self.pogledaj() is not None:
            raise ValueError("Višak znakova u formuli.")

        return literali


def parsiraj_klauzulu(tekst):
    return Parser(tekst).parsiraj_klauzulu()


# SUPSTITUCIJA I UNIFIKACIJA

def primijeni_supstituciju(termin, supstitucija):
    tip = termin[0]

    if tip == "var":
        ime = termin[1]

        if ime in supstitucija:
            return primijeni_supstituciju(
                supstitucija[ime], supstitucija
            )

        return termin

    if tip == "func":
        argumenti = []

        for argument in termin[2]:
            argumenti.append(
                primijeni_supstituciju(argument, supstitucija)
            )

        return ("func", termin[1], argumenti)

    return termin


def pojavljuje_se(varijabla, termin, supstitucija):
    termin = primijeni_supstituciju(termin, supstitucija)

    if termin[0] == "var":
        return termin[1] == varijabla

    if termin[0] == "func":
        for argument in termin[2]:
            if pojavljuje_se(varijabla, argument, supstitucija):
                return True

    return False


def unificiraj(termin1, termin2):
    supstitucija = {}
    parovi = [(termin1, termin2)]

    while parovi:
        prvi, drugi = parovi.pop()

        prvi = primijeni_supstituciju(prvi, supstitucija)
        drugi = primijeni_supstituciju(drugi, supstitucija)

        if prvi == drugi:
            continue

        if prvi[0] == "var":
            ime = prvi[1]

            if pojavljuje_se(ime, drugi, supstitucija):
                return None

            supstitucija[ime] = drugi
            continue

        if drugi[0] == "var":
            ime = drugi[1]

            if pojavljuje_se(ime, prvi, supstitucija):
                return None

            supstitucija[ime] = prvi
            continue

        if prvi[0] != drugi[0]:
            return None

        if prvi[0] == "const":
            return None

        if prvi[1] != drugi[1]:
            return None

        argumenti1 = prvi[2]
        argumenti2 = drugi[2]

        if len(argumenti1) != len(argumenti2):
            return None

        for i in range(len(argumenti1)):
            parovi.append((argumenti1[i], argumenti2[i]))

    return supstitucija


def unificiraj_literale(literal1, literal2):
    negacija1, predikat1, argumenti1 = literal1
    negacija2, predikat2, argumenti2 = literal2

    if negacija1 == negacija2:
        return None

    if predikat1 != predikat2:
        return None

    if len(argumenti1) != len(argumenti2):
        return None

    supstitucija = {}

    for i in range(len(argumenti1)):
        nova = unificiraj(
            primijeni_supstituciju(argumenti1[i], supstitucija),
            primijeni_supstituciju(argumenti2[i], supstitucija)
        )

        if nova is None:
            return None

        supstitucija.update(nova)

    return supstitucija


# OBRADA KLAUZULA

def primijeni_na_literal(literal, supstitucija):
    negacija, predikat, argumenti = literal
    novi_argumenti = []

    for argument in argumenti:
        novi_argumenti.append(
            primijeni_supstituciju(argument, supstitucija)
        )

    return (negacija, predikat, novi_argumenti)


def primijeni_na_klauzulu(klauzula, supstitucija):
    nova = []

    for literal in klauzula:
        nova.append(primijeni_na_literal(literal, supstitucija))

    return nova


def prikupi_varijable(termin, varijable):
    if termin[0] == "var":
        varijable.add(termin[1])

    if termin[0] == "func":
        for argument in termin[2]:
            prikupi_varijable(argument, varijable)


def standardiziraj_apart(klauzula, zauzete):
    mapa = {}

    def preimenuj(termin):
        if termin[0] == "var":
            ime = termin[1]

            if ime not in mapa:
                i = 0

                while "v" + str(i) in zauzete:
                    i += 1

                novo_ime = "v" + str(i)
                zauzete.add(novo_ime)
                mapa[ime] = ("var", novo_ime)

            return mapa[ime]

        if termin[0] == "func":
            argumenti = []

            for argument in termin[2]:
                argumenti.append(preimenuj(argument))

            return ("func", termin[1], argumenti)

        return termin

    nova = []

    for negacija, predikat, argumenti in klauzula:
        novi_argumenti = []

        for argument in argumenti:
            novi_argumenti.append(preimenuj(argument))

        nova.append((negacija, predikat, novi_argumenti))

    return nova


def kljuc_klauzule(klauzula):
    mapa = {}

    def normaliziraj(termin):
        if termin[0] == "var":
            ime = termin[1]

            if ime not in mapa:
                mapa[ime] = "v" + str(len(mapa))

            return ("var", mapa[ime])

        if termin[0] == "func":
            argumenti = []

            for argument in termin[2]:
                argumenti.append(normaliziraj(argument))

            return ("func", termin[1], tuple(argumenti))

        return termin

    literali = []

    for negacija, predikat, argumenti in klauzula:
        novi_argumenti = []

        for argument in argumenti:
            novi_argumenti.append(normaliziraj(argument))

        literali.append((negacija, predikat, tuple(novi_argumenti)))

    return tuple(sorted(literali, key=str))


def je_tautologija(klauzula):
    for i in range(len(klauzula)):
        for j in range(i + 1, len(klauzula)):
            prvi = klauzula[i]
            drugi = klauzula[j]

            if prvi[0] == drugi[0]:
                continue

            if prvi[1] != drugi[1]:
                continue

            if prvi[2] == drugi[2]:
                return True

    return False


# ISPIS

def termin_u_tekst(termin):
    if termin[0] == "var":
        return termin[1]

    if termin[0] == "const":
        return termin[1]

    argumenti = []

    for argument in termin[2]:
        argumenti.append(termin_u_tekst(argument))

    return termin[1] + "(" + ", ".join(argumenti) + ")"


def literal_u_tekst(literal):
    negacija, predikat, argumenti = literal
    tekst = predikat + "("

    tekst += ", ".join(
        termin_u_tekst(argument) for argument in argumenti
    )

    tekst += ")"

    if negacija:
        return "~" + tekst

    return tekst


def klauzula_u_tekst(klauzula):
    if len(klauzula) == 0:
        return "□"

    tekst = []

    for literal in klauzula:
        tekst.append(literal_u_tekst(literal))

    return " | ".join(tekst)


def supstitucija_u_tekst(supstitucija):
    if not supstitucija:
        return "{}"

    dijelovi = []

    for varijabla in sorted(supstitucija):
        vrijednost = termin_u_tekst(supstitucija[varijabla])
        dijelovi.append(varijabla + " = " + vrijednost)

    return "{ " + ", ".join(dijelovi) + " }"


# REZOLUCIJA


def razrijesi(klauzula1, klauzula2):
    zauzete = set()

    for literal in klauzula1 + klauzula2:
        for argument in literal[2]:
            prikupi_varijable(argument, zauzete)

    klauzula2 = standardiziraj_apart(klauzula2, zauzete)
    rezultati = []

    for i in range(len(klauzula1)):
        for j in range(len(klauzula2)):
            literal1 = klauzula1[i]
            literal2 = klauzula2[j]

            supstitucija = unificiraj_literale(literal1, literal2)

            if supstitucija is None:
                continue

            nova = []

            for k in range(len(klauzula1)):
                if k != i:
                    nova.append(klauzula1[k])

            for k in range(len(klauzula2)):
                if k != j:
                    nova.append(klauzula2[k])

            nova = primijeni_na_klauzulu(nova, supstitucija)

            jedinstveni = []

            for literal in nova:
                if literal not in jedinstveni:
                    jedinstveni.append(literal)

            if je_tautologija(jedinstveni):
                continue

            rezultati.append((jedinstveni, supstitucija, i, j))

    return rezultati

def rezolucija(klauzule, najveci_broj=1000):
    poznate = []
    kljucevi = set()

    for klauzula in klauzule:
        kljuc = kljuc_klauzule(klauzula)

        if kljuc not in kljucevi:
            poznate.append(klauzula)
            kljucevi.add(kljuc)

    print("\nPOČETNE KLAUZULE")

    for i in range(len(poznate)):
        print("K" + str(i + 1) + ": " + klauzula_u_tekst(poznate[i]))

    if any(len(klauzula) == 0 for klauzula in poznate):
        print("\nPrazna klauzula već je prisutna.")
        return True

    indeks = 0

    while indeks < len(poznate):
        prva = poznate[indeks]

        for j in range(indeks):
            druga = poznate[j]

            rezultati = razrijesi(prva, druga)

            for rezultat in rezultati:
                nova, supstitucija, _, _ = rezultat
                kljuc = kljuc_klauzule(nova)

                if kljuc in kljucevi:
                    continue

                poznate.append(nova)
                kljucevi.add(kljuc)

                broj = len(poznate)

                print("\nK" + str(broj) + ": " + klauzula_u_tekst(nova))
                print("Dobivena rezolucijom K" + str(indeks + 1)
                      + " i K" + str(j + 1))
                print("Unifikator:", supstitucija_u_tekst(supstitucija))

                if len(nova) == 0:
                    print("\nDOKAZANO: skup klauzula je nezadovoljiv.")
                    return True

                if len(poznate) >= najveci_broj:
                    print("\nDosegnut je najveći broj klauzula.")
                    return None

        indeks += 1

    print("\nNije pronađena prazna klauzula.")
    print("Postupak rezolucije nije pronašao dokaz nezadovoljivosti.")
    return False


# UNOS I INTERPRETACIJA

def glavni_program():
    print("REZOLUCIJA U LOGICI PRVOG REDA")
    print("--------------------------------")
    print("Unesite jednu klauzulu po retku.")
    print("Za kraj unesite prazan red.")
    print()

    klauzule = []

    while True:
        tekst = input("Klauzula: ").strip()

        if tekst == "":
            break

        try:
            klauzule.append(parsiraj_klauzulu(tekst))
        except ValueError as greska:
            print("Greška:", greska)

    if not klauzule:
        print("Nije unesena nijedna klauzula.")
        return

    rezolucija(klauzule)


if __name__ == "__main__":
    glavni_program()
