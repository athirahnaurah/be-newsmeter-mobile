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
            "MATCH(u:User {email: $email})-[r:HAS_PREFERENCE]->(k:Category) RETURN k.name",
            email=email,
        )
        data = []
        for record in result:
            data.append((record["k.name"]))
        return data

    def find_history(session, email, mongoID):
        result = session.run(
            "MATCH (u:User)-[r:HAS_READ]->(b:News) WHERE u.email = $email AND b.mongoID = $mongoID RETURN b.title, b.content",
            email=email,
            mongoID=mongoID,
        )
        return result.single()

    def find_history_media(session, email):
        result = session.run(
            "MATCH p=(u:User {email: $email})-[r:HAS_READ]->()-[r2:FROM]->(m:Media) RETURN m.name",
            email=email,
        )
        media = []
        for record in result:
            media.append((record["m.name"]))
        return media

    def find_history_periodly(session, email, start, end):
        result = session.run(
            "MATCH (u:User {email: $email})-[r:HAS_READ]->(b:News)-[r2:FROM]->(m:Media) WHERE r.datetime >= $start and r.datetime <= $end return u.email, b.mongoID, b.original, b.title, b.content, b.date, b.image, r.datetime, m.name, id(r)",
            email=email,
            start=start,
            end=end,
        )
        data = []
        news = {}
        for record in result:
            news["user"] = record["u.email"]
            news["datetime"] = record["r.datetime"]
            news["media"] = record["m.name"]
            news["_id"] = record["b.mongoID"]
            news["original"] = record["b.original"]
            news["title"] = record["b.title"]
            news["content"] = record["b.content"]
            news["image"] = record["b.image"]
            news["date"] = record["b.date"]
            news["id_has_read"] = record["id(r)"]
            data.append(news.copy())
        return data

    def find_reader(session, start, end):
        result = session.run(
            "MATCH (b:User)-[r1:HAS_READ]->(nh:News) WHERE r1.datetime >= $start and r1.datetime <= $end RETURN DISTINCT b.email",
            start=start,
            end=end,
        )
        user = []
        for record in result:
            user.append((record["b.email"]))
        return user

    def save_history(session, email, mongoID, time):
        result = session.run(
            "MATCH (a:User), (b:News) WHERE a.email = $email AND b.mongoID = $mongoID CREATE (a)-[r: HAS_READ {datetime: $time}]->(b) RETURN a,b",
            email=email,
            mongoID=mongoID,
            time=time,
        )
        return result

    def create_relation_recommend(session, email, recomID, index):
        result = session.run(
            "MATCH (a:User), (b:News) WHERE a.email = $email AND b.mongoID = $mongoID CREATE (b)-[r: RECOMMENDED_TO {index: $index}]->(a) RETURN a, b",
            email=email,
            mongoID=recomID,
            index=index,
        )
        return result

    def get_recommendation(session, email):
        result = session.run(
            "MATCH (b:User)-[r1:HAS_READ]->(nh:News)-[r2:SIMILAR]->(a:News)-[r3:RECOMMENDED_TO]->(b:User) WHERE b.email = $email RETURN a.mongoID, a.original, a.title, a.content, a.date, a.image, r3.index, r2.score ORDER BY r3.index DESC LIMIT 45",
            email=email,
        )
        data = []
        news = {}
        for record in result:
            news["_id"] = record["a.mongoID"]
            news["original"] = record["a.original"]
            news["title"] = record["a.title"]
            news["content"] = record["a.content"]
            news["image"] = record["a.image"]
            news["date"] = record["a.date"]
            news["index"] = record["r3.index"]
            news["score"] = record["r2.score"]
            data.append(news.copy())
        return data
