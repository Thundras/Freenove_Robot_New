import pytest
from brain.bt_core import Selector, Sequence, Leaf

class ActionLeaf(Leaf):
    def __init__(self, name, returns):
        super().__init__(name)
        self.returns = returns
        self.called = False
    def run(self):
        self.called = True
        return self.returns

def test_selector_success():
    """Selector returns success as soon as one child succeeds"""
    l1 = ActionLeaf("L1", False)
    l2 = ActionLeaf("L2", True)
    l3 = ActionLeaf("L3", True)
    
    sel = Selector("TestSelector", [l1, l2, l3])
    result = sel.run()
    
    assert result is True
    assert l1.called is True
    assert l2.called is True
    assert l3.called is False # Should stop after success

def test_sequence_failure():
    """Sequence returns failure as soon as one child fails"""
    l1 = ActionLeaf("L1", True)
    l2 = ActionLeaf("L2", False)
    l3 = ActionLeaf("L3", True)
    
    seq = Sequence("TestSequence", [l1, l2, l3])
    result = seq.run()
    
    assert result is False
    assert l1.called is True
    assert l2.called is True
    assert l3.called is False # Should stop after failure
