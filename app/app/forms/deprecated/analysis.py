from fastapi import Form


class AnalysisUpdateForm:
    def __init__(self,
                 name: str = Form(default=None),
                 description: str = Form(default=None),
                 ):
        self.name = name
        self.description = description
