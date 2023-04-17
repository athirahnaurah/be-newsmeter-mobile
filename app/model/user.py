from neo4j import GraphDatabase, basic_auth

class User:
    def __init__(self, name, email, password, id=None):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
    
    def create(self, session):
        result = session.run("CREATE (u:User {name: $name, email: $email, password: $password}) RETURN id(u)", name=self.name, email = self.email,password=self.password)
        self.id = result.single()[0]

    def find_by_email(session, email):
        result = session.run("MATCH (u:User {email: $email}) RETURN u.name as name, u.email as email, u.password as password", email=email)
        record = result.single()
        if record:
            return User(name=record['name'], email=record['email'], password=record['password'])
        else:
            return None

    def create_preference(session,email,kategori):
        for k in kategori:
            result = session.run(
                "MATCH (a:User {email: $email}), (b:Kategori {name: $kategori})"
                "CREATE (a)-[r: HAS_PREFERENCE]->(b) RETURN a.email, b.name", 
                email=email, kategori = k
                )
        return result
    
    def find_preference(session, email):
        result = session.run("MATCH(u:User {email: $email})-[r:HAS_PREFERENCE]->(k:Kategori) RETURN k.name", email=email)
        data = []
        for record in result:
            data.append((record["k.name"]))
        return data

    def find_history(session, email, mongoID):
        result = session.run("MATCH (u:User)-[r:HAS_READ]->(b:Berita) WHERE u.email = $email AND b.mongoID = $mongoID RETURN b.title, b.content", email = email, mongoID = mongoID)
        return result.single()
    
    def find_history_periodly(session, email, start, end):
        result = session.run("MATCH (u:User {email: $email})-[r:HAS_READ]->(b:Berita) WHERE r.timestamp >= $start and r.timestamp <= $end return u.email, b.mongoID, b.content, b.date", email = email, start = start, end = end)
        data =[]
        news = {}
        for record in result:
            news["user"] = record["u.email"]
            news["id_berita"] = record["b.mongoID"]
            news["content"] = record["b.content"]
            news["waktu_terbit"] = record["b.date"]
            data.append(news.copy())
        return data
    
    def save_history(session, email, mongoID, time):
        result = session.run("MATCH (a:User), (b:Berita) WHERE a.email = $email AND b.mongoID = $mongoID CREATE (a)-[r: HAS_READ {timestamp: $time}]->(b) RETURN a,b", email = email, mongoID = mongoID, time = time)
        return result
