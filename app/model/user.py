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
    
    # def find_by_activation_token(session, token):
    #     result = session.run("MATCH (u:User {activation_token: $token}) RETURN u.name as name, u.email as email, u.password as password", token=token)
    #     record = result.single()
    #     if record:
    #         return User(name=record['name'], email=record['email'], password=record['password'])
    #     else:
    #         return None
    
    # def activate(self, session):
    #     session.run("MATCH (u:User {email: $email}) SET u.active = true RETURN u", email=self.email)

    def create_preference(session,email,kategori):
        for a in kategori:
            session.run("MATCH (a:User {email: $email}), (b:Kategori {name: $kategori}) CREATE (a)-[r: HAS_PREFERENCE]->(b) RETURN a,b",email=email,kategori=a)