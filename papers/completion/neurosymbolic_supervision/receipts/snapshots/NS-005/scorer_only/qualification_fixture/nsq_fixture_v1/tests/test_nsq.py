from nsq_fixture.core import add, process, authorize
def test_add():
    assert add(1, 2) == 3
def test_process():
    assert process([1, 2]) == [2, 3]
def test_authorize():
    assert authorize('admit-ok') is True
