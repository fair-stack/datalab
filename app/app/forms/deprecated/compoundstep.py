from fastapi import Form


class CompoundStepUpdateForm:
    def __init__(self,
                 name: str = Form(default=None),
                 description: str = Form(default=None),
                 instruction: str = Form(default=None),
                 multitask_mode: str = Form(default=None)
                 ):
        self.name = name
        self.description = description
        self.instruction = instruction
        self.multitask_mode = multitask_mode
