class FooParser:
    @staticmethod
    def foo(data, index=None):
        if index is None:
            return data
        return data[index]

    @classmethod
    def spam(cls, data, index=None):
        if index is None:
            return data
        return data[index]

    def bar(self, index=None):
        if index is None:
            return self.data
        return self.data[index]


def foo_parser(data, index=None):
    if index is None:
        return data
    return data[index]
