class Category:
    def __init__(self, name, id=None):
        self.id = id
        self.name = name

    def get_relation_category(session, mongoID):
        result = session.run(
            "MATCH (b:News)-[:HAS_A]->(k:Category) WHERE b.mongoID = $mongoID return k.name",
            mongoID=mongoID,
        )
        return result.single()[0]
