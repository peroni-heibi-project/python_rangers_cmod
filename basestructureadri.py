from json import load                    # per leggere il file JSON
from sqlite3 import connect              # per connettersi a SQLite
from pandas import DataFrame, read_sql  # per costruire tabelle e interrogare SQLite


# ===========================================================================
# LIVELLO 1 — DATA MODEL
# Classi Python pure: nessun database, nessun file.
# I costruttori NON prendono parametri (come richiesto dalle istruzioni).
# Si usano i metodi set* per popolare gli oggetti dopo la creazione.
# ===========================================================================


class IdentifiableEntity:
    """
    Classe radice della gerarchia del data model.
    Qualunque entità che possiede un identificatore (DOI, OMID, ISSN, ecc.)
    estende questa classe.
    L'attributo 'id' è una lista perché la stessa entità può avere
    più identificatori (es. sia un DOI che un OMID).
    """

    def __init__(self):
        self.id = list()

    def getId(self):
        # Restituiamo una copia per proteggere l'attributo interno
        return list(self.id)

    def setId(self, identifiers):
        self.id = list(identifiers)


class BibliographicEntity(IdentifiableEntity):
    """
    Rappresenta una pubblicazione accademica (articolo, libro, capitolo...).
    Eredita getId() da IdentifiableEntity.
    """

    def __init__(self):
        super().__init__()
        self.title = ""
        self.publicationDate = ""
        self.authors = list()   # lista di oggetti Person
        self.venues = list()    # lista di oggetti Venue

    def getTitle(self):
        return self.title

    def getPublicationDate(self):
        return self.publicationDate

    def getAuthors(self):
        return list(self.authors)

    def getVenues(self):
        return list(self.venues)

    def setTitle(self, title):
        self.title = title

    def setPublicationDate(self, date):
        self.publicationDate = date

    def setAuthors(self, authors):
        self.authors = list(authors)

    def setVenues(self, venues):
        self.venues = list(venues)


class Person:
    """
    Rappresenta un autore di una pubblicazione.
    Nel JSON il formato è "Cognome, Nome": il parsing lo fa l'handler.
    """

    def __init__(self):
        self.givenName = ""
        self.familyName = ""

    def getGivenName(self):
        return self.givenName

    def getFamilyName(self):
        return self.familyName

    def setGivenName(self, name):
        self.givenName = name

    def setFamilyName(self, name):
        self.familyName = name


class Venue(IdentifiableEntity):
    """
    Rappresenta la rivista o il libro in cui è stata pubblicata un'entità.
    Eredita getId() da IdentifiableEntity.
    """

    def __init__(self):
        super().__init__()
        self.title = ""

    def getTitle(self):
        return self.title

    def setTitle(self, title):
        self.title = title


class Citation(IdentifiableEntity):
    """
    Rappresenta una citazione: il legame tra chi cita (citingEntity)
    e chi è citato (citedEntity). Entrambi sono oggetti BibliographicEntity.
    Eredita getId() da IdentifiableEntity.
    """

    def __init__(self):
        super().__init__()
        self.citingEntity = None  # oggetto BibliographicEntity
        self.citedEntity  = None  # oggetto BibliographicEntity
        self.creationDate = ""    # es. "2020"
        self.timespan     = ""    # es. "P2Y3M" (ISO 8601 duration)

    def getCitingEntity(self):
        return self.citingEntity

    def getCitedEntity(self):
        return self.citedEntity

    def getCreationDate(self):
        return self.creationDate

    def getTimespan(self):
        return self.timespan

    def setCitingEntity(self, entity):
        self.citingEntity = entity

    def setCitedEntity(self, entity):
        self.citedEntity = entity

    def setCreationDate(self, date):
        self.creationDate = date

    def setTimespan(self, timespan):
        self.timespan = timespan


class AuthorSelfCitation(Citation):
    """
    Citazione in cui almeno un autore è autore sia dell'entità
    citante che di quella citata. Eredita tutto da Citation.
    """

    def __init__(self):
        super().__init__()


class JournalSelfCitation(Citation):
    """
    Citazione in cui la venue dell'entità citante coincide con
    quella dell'entità citata. Eredita tutto da Citation.
    """

    def __init__(self):
        super().__init__()