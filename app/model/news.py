
class News:
    def __init__(self, mongoID, original, title, content, image, date, id=None):
        self.id = id
        self.mongoID = mongoID
        self.original = original
        self.title = title
        self.content = content
        self.image = image
        self.date = date

    def save_news(self, session):
        result = session.run("CREATE (n:Berita {mongoID: $mongoID, original: $original, title: $title, content: $content, image: $image, date: $date}) RETURN n", mongoID = self.mongoID, original = self.original, title = self.title, content = self.content, image = self.image, date = self.date)
        self.id = result.single()[0]

    def find_news(session, mongoID):
        result = session.run("MATCH (n:Berita {mongoID: $mongoID}) RETURN n", mongoID = mongoID)
        return result.single()

    def create_relation_to_media(session, mongoID, media):
        result = session.run("MATCH (a:Berita), (b:Media) WHERE b.name = $name AND a.mongoID = $mongoID CREATE (a)-[r: FROM]->(b) RETURN a,b", name = media, mongoID = mongoID)
        return result
