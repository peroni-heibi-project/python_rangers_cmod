# ===============================================================================
# CLASSE BASE: Handler
# Contiene il percorso/URL del database
# ===============================================================================

class Handler:
    def __init__(self):
        self.dbPathOrUrl = "" #parte vuota, si imposta dopo

    def getDbPathOrUrl(self):
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, pathOrUrl):
        self.dbPathOrUrl = pathOrUrl
        return True
    
# ===============================================================================
# UploadHandler - figlia di Handler
# Definisce il metodo pushDataToDb (astratto qui, poi implementato nelle sottoclassi)
# ===============================================================================

class UploadHandler(Handler):
    def __init__(self):
        super().__init__() # chiama il costruttore di Handler

    def pushDataToDb(self, path): #le sottoclassi implementeranno questa logica
        pass

# ===============================================================================
# Query-Handler - figlia di Handler
# Definisce il metodo getById (astratto qui, poi implementato nelle sottoclassi)
# ===============================================================================

class QueryHandler(Handler):
    def __init__(self):
        super().__init__() # chiama il costruttore di Handler

    def getById(self, id): # le sottoclassi implementeranno questa logica
        pass

# ===============================================================================
# CitationUploadHandler - PARTE MIA!!!
# Legge CSV e carica nel database a grafo (Blazegraph)
# ===============================================================================

class CitationUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__() # chiama il costruttore di UploadHandler

    def pushDataToDb(self, path):
        #Qui implementerò la lettura del CSV e il caricamento in Blazegraph via SPARQL
        pass

# ===============================================================================
# BibliographicEntityUploadHandler - PARTE DI ADRIANA!!!
# Legge JSON e carica nel database relazionale (SQLite)
# ===============================================================================

class BibliographicEntityUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):
        #qui va implementata la lettura del JSON e il caricamento in SQLite
        pass

# ===============================================================================
# CitationQueryHandler - PARTE MIA!!!
# Interroga il database a grafo (Blazegraph) e restituisce DataFrame
# ===============================================================================

class CitationQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

    def getAllCitations(self):
        pass

    def getAllAuthorSelfCitations(self):
        pass

    def getAllJournalSelfCitations(self):
        pass

    def getCitationsWithinTimespan(self, min_timespan, max_timespan):
        pass

    def getCitationsWithinDate(self, start_date, end_date):
        pass

# ===============================================================================
# BibliographicEntityQueryHandler - PARTE DI ADRIANA
# Interroga il database relazionale e restituisce DataFrame
# ===============================================================================

class BibliographicEntityQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

    def getAllBibliographicEntities(self):
        pass

    def getBibliographicEntitiesWithTitle(self, title):
        pass

    def getBibliographicEntitiesWithAuthor(self, author):
        pass

    def getBibliographicEntitiesWithinPublicationDate(self, start_date, end_date):
        pass

    def getBibliographicEntitiesWithVenue(self, venue):
        pass
