# BASE CLASS: THE HANDLER

class Handler:
    def __init__(self):
        self.dbPathOrUrl = ""

    def getDbPathOrUrl(self):
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, pathOrUrl):
        self.dbPathOrUrl = pathOrUrl
        return True
    
# SECONDARY CLASS: UploadHandler - figlia di Handler

class UploadHandler(Handler):
    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):
        pass

# SECONDARY CLASS: QueryHandler - figlia di Handler

class QueryHandler(Handler):
    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

# TERTIARY CLASS: CitationUploadHandler - figlia di UploadHandler

class CitationUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__()
    
    def pushDataToDb(self, path):
        pass

# TERTIARY CLASS: BibliographicEntityUploadHandler - figlia di UploadHandler (parte che deve popolare adri)

#class BibliographicEntityUploadHandler(UploadHandler):
#    def __init__(self):
#        super().__init__()
#
#    def pushDataToDb(self, path):
#        pass

# TERTIARY CLASS: CitationQueryHandler - figlia di QueryHandler

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

# TERTIARY CLASS: BibliographicEntityQueryHandler - figlia di QueryHandler (parte di adri)

#...
#...
#...
