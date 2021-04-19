class Ticket:
    def __init__(
        self, subject="", problem_description="", requestor="", cc="", owner=""
    ):
        self.subject = subject
        self.problem_description = problem_description
        self.requestor = requestor
        self.cc = cc
        self.owner = owner
