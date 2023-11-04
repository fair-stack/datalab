from fastapi import Form


class AnalysisStepUpdateForm:
    def __init__(self,
                 state: str = Form(default=None)
                 ):
        self.state = state
