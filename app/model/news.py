
class News:
    def __init__(self, mongoID, original, title, content, image, date, media, category, id=None):
        self.id = id
        self.mongoID = mongoID
        self.original = original
        self.title = title
        self.content = content
        self.image = image
        self.category = category
        self.media = media
        self.date = date

    def save_news(self, session):
        result = session.run("MATCH (k:Category), (m:Media) WHERE m.name = $media <> k.name = $category CREATE (b:News {mongoID: $mongoID, original: $original, title: $title, content: $content, image: $image, date: $date})-[:FROM]->(m) ,(b)-[:HAS_A]->(k) RETURN b", media = self.media, category = self.category, mongoID = self.mongoID, original = self.original, title = self.title, content = self.content, image = self.image, date = self.date)
        self.id = result.single()[0]

    def find_news(session, mongoID):
        result = session.run("MATCH (n:News {mongoID: $mongoID}) RETURN n", mongoID = mongoID)
        return result.single()

    def create_relation_similar(session, historyID, recomID, value):
        result = session.run("MATCH (a:News), (b:News) WHERE a.mongoID = $history AND b.mongoID = $recom CREATE (a)-[r:SIMILAR {score: $score}]->(b) RETURN a,b", history = historyID, recom = recomID, score = value)
        return result

    def get_similarity(session, recomID):
        result = session.run("MATCH(b:News)-[r:SIMILAR]->(br:News) WHERE br.mongoID = $_id return r.score", _id = recomID)
        return result.single()[0]

    def get_index_max(session, email):
        result = session.run("MATCH (n:News)-[r:RECOMMENDED_TO]->(u:User) WHERE u.email = $email RETURN r.index ORDER BY r.index DESC LIMIT 1", email = email)
        return result.single()[0]
    
    def check_relation_recommend(session, email):
        result = session.run("MATCH (n:News)-[r:RECOMMENDED_TO]->(u:User) WHERE u.email = $email RETURN r", email = email)
        return result.single()