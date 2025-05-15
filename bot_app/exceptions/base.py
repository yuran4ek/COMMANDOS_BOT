class BotAppError(Exception):
    """
    Базовое исключение для всего приложения бота.
    """
    def __init__(self, *args):
        self.extra_info = args[0] if args else None
        super().__init__(*args)

    def __str__(self):
        base = self.__doc__ or 'Неизвестная ошибка!'
        return f'{base} {self.extra_info}' if self.extra_info else base

    @classmethod
    def from_exception(cls, e: Exception):
        return cls(f'{e.__class__.__name__}: {e}')
