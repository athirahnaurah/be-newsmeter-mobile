
class News:
    def __init__(self, mongoID, original, title, content, image, date, media, kategori, id=None):
        self.id = id
        self.mongoID = mongoID
        self.original = original
        self.title = title
        self.content = content
        self.image = image
        self.kategori = kategori
        self.media = media
        self.date = date

    def save_news(self, session):
        result = session.run("MATCH (k:Kategori), (m:Media) WHERE m.name = $media <> k.name = $kategori CREATE (b:Berita {mongoID: $mongoID, original: $original, title: $title, content: $content, image: $image, date: $date})-[:FROM]->(m) ,(b)-[:HAS_A]->(k) RETURN b", media = self.media, kategori = self.kategori, mongoID = self.mongoID, original = self.original, title = self.title, content = self.content, image = self.image, date = self.date)
        self.id = result.single()[0]

    def find_news(session, mongoID):
        result = session.run("MATCH (n:Berita {mongoID: $mongoID}) RETURN n", mongoID = mongoID)
        return result.single()

    # def create_relation_to_media(session, mongoID, media):
    #     result = session.run("MATCH (a:Berita), (b:Media) WHERE b.name = $name AND a.mongoID = $mongoID CREATE (a)-[r: FROM]->(b) RETURN a,b", name = media, mongoID = mongoID)
    #     return result

    def create_relation_similar(session, historyID, recomID, value):
        result = session.run("MATCH (a:Berita), (b:Berita) WHERE a.mongoID = $history AND b.mongoID = $recom CREATE (a)-[r:SIMILAR {score: $score}]->(b) RETURN a,b", history = historyID, recom = recomID, score = value)
        return result

    def get_similarity(session, recomID):
        result = session.run("MATCH(b:Berita)-[r:SIMILAR]->(br:Berita) WHERE br.mongoID = $_id return r.score", _id = recomID)
        return result.single()[0]
