class Category:
    def __init__(self, name, id=None):
        self.id = id
        self.name = name
    
    def create_relation_to_news(session, mongoID, category):
        result = session.run("MATCH (a:Kategori), (b:Berita) WHERE a.name = $name AND b.mongoID = $mongoID CREATE (a)-[r: HAS_A]->(b) RETURN a,b", name = category, mongoID = mongoID)
        return result