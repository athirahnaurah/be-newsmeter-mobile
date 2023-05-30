class Media:
    def __init__(self, name, view, id=None):
        self.id = id
        self.name = name
        self.view = view

    def get_relation_media(session, mongoID):
        result = session.run("MATCH (b:News)-[:FROM]->(m:Media) WHERE b.mongoID = $mongoID return m.name", mongoID=mongoID)
        return result.single()[0]
    
    def set_total_view(session, total, media):
        result = session.run("MATCH (m:Media) WHERE m.name = $name SET m.view = $view", name = media, view = total)
        return result
    
    def find_total_view(session, media):
        result = session.run("MATCH(m:Media) WHERE m.name = $name return m.view", name = media)
        return result.single()[0]

    def get_all_media(session):
        result = session.run("MATCH(m:Media) RETURN m.name, m.view")
        data = []
        media = {}
        for record in result:
            media["name"] = record["m.name"]
            media["view"] = record["m.view"]
            data.append(media.copy())
        return data
    


    
    