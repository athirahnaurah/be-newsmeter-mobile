from neo4j import GraphDatabase, basic_auth


class User:
    def __init__(self, name, email, password, id=None):
        self.id = id
        self.name = name
        self.email = email
        self.password = password

    def create(self, session):
        result = session.run(
            "CREATE (u:User {name: $name, email: $email, password: $password}) RETURN id(u)",
            name=self.name,
            email=self.email,
            password=self.password,
        )
        self.id = result.single()[0]

    def find_by_email(session, email):
        result = session.run(
            "MATCH (u:User {email: $email}) RETURN u.name as name, u.email as email, u.password as password",
            email=email,
        )
        record = result.single()
        if record:
            return User(
                name=record["name"], email=record["email"], password=record["password"]
            )
        else:
            return None

    def create_preference(session, email, kategori):
        for k in kategori:
            result = session.run(
                "MATCH (a:User {email: $email}), (b:Category {name: $kategori})"
                "CREATE (a)-[r: HAS_PREFERENCE]->(b) RETURN a.email, b.name",
                email=email,
                kategori=k,
            )
        return result

    def find_preference(session, email):
        result = session.run(
            "MATCH(u:User {email: $email})-[r:HAS_PREFERENCE]->(k:Kategori) RETURN k.name",
            email=email,
        )
        data = []
        for record in result:
            data.append((record["k.name"]))
        return data

    def find_history(session, email, mongoID):
        result = session.run(
            "MATCH (u:User)-[r:HAS_READ]->(b:Berita) WHERE u.email = $email AND b.mongoID = $mongoID RETURN b.title, b.content",
            email=email,
            mongoID=mongoID,
        )
        return result.single()

    def find_history_media(session, email):
        result = session.run("MATCH p=(u:User {email: $email})-[r:HAS_READ]->()-[r2:FROM]->(m:Media) RETURN m.name", email = email)
        media = []
        for record in result:
            media.append((record["m.name"]))
        return media

    def find_history_periodly(session, email, start, end):
        result = session.run(
            "MATCH (u:User {email: $email})-[r:HAS_READ]->(b:Berita)-[r2:FROM]->(m:Media) WHERE r.timestamp >= $start and r.timestamp <= $end return u.email, b.mongoID, b.original, b.title, b.content, b.date, b.image, r.timestamp, m.name",
            email=email,
            start=start,
            end=end,
        )
        data = []
        news = {}
        for record in result:
            news["user"] = record["u.email"]
            news["timestamp"] = record["r.timestamp"]
            news["media"] = record["m.name"]
            news["_id"] = record["b.mongoID"]
            news["original"] = record["b.original"]
            news["title"] = record["b.title"]
            news["content"] = record["b.content"]
            news["image"] = record["b.image"]
            news["date"] = record["b.date"]
            data.append(news.copy())
        return data

    def save_history(session, email, mongoID, time):
        result = session.run(
            "MATCH (a:User), (b:Berita) WHERE a.email = $email AND b.mongoID = $mongoID CREATE (a)-[r: HAS_READ {timestamp: $time}]->(b) RETURN a,b",
            email=email,
            mongoID=mongoID,
            time=time,
        )
        return result

    def create_relation_recommend(session, email, recomID, index):
        result = session.run(
            "MATCH (a:User), (b:Berita) WHERE a.email = $email AND b.mongoID = $mongoID CREATE (a)-[r: HAS_RECOMMEND {index: $index}]->(b) RETURN a, b",
            email=email,
            mongoID=recomID,
            index=index,
        )
        return result

    def get_recommendation(session, email):
        result = session.run(
            "match (a:User)-[r:HAS_RECOMMEND]->(b:Berita) WHERE a.email = $email RETURN b.mongoID, b.original, b.title, b.content, b.date, b.image, r.index ORDER BY r.index DESC LIMIT 45",
            email=email,
        )
        data = []
        news = {}
        for record in result:
            news["_id"] = record["b.mongoID"]
            news["original"] = record["b.original"]
            news["title"] = record["b.title"]
            news["content"] = record["b.content"]
            news["image"] = record["b.image"]
            news["date"] = record["b.date"]
            news["index"] = record["r.index"]
            data.append(news.copy())
        return data
