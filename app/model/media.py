class Media:
    def __init__(self, name, id=None):
        self.id = id
        self.name = name

    def get_relation_media(session, mongoID):
        result = session.run("MATCH (b:News)-[:FROM]->(m:Media) WHERE b.mongoID = $mongoID return m.name", mongoID=mongoID)
        return result.single()[0]
    


    
    