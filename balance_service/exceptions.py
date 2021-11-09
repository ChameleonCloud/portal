class MissingAuthInformation(Exception):
    message = "Missing authentication token"


class AuthURLException(Exception):
    def __init__(
        self, auth_url, message=("Auth URL {} not in allowed_auth_urls list.")
    ):
        self.auth_url = auth_url
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message.format(self.auth_url)


class AuthUserException(Exception):
    def __init__(self, user, message=("User {} not in authorized users list.")):
        self.user = user
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message.format(self.user)
