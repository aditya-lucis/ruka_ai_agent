import pytest
from src.state.core import InternalState
from src.expression.params import Expression, EyeMood, EarPose, params_for
from src.expression.engine import ExpressionEngine, SocialCue
from src.emotion.appraisal import EmotionalSignal

def test_params_for_returns_copy():
    p1 = params_for(Expression.HAPPY)
    p2 = params_for(Expression.HAPPY)
    assert p1 == p2
    assert p1 is not p2
    p1.motion_energy = 0.99
    assert p2.motion_energy != 0.99

def test_decide_tool_executing_override():
    state = InternalState()
    engine = ExpressionEngine(state)
    
    # State neutral -> tool_executing gives FOCUSED
    res = engine.decide(phase="tool_executing")
    assert res.expression == Expression.FOCUSED
    assert state.expression.expression == Expression.FOCUSED.value

def test_decide_thinking_override():
    state = InternalState()
    engine = ExpressionEngine(state)
    
    res = engine.decide(phase="thinking")
    assert res.expression == Expression.THINKING

def test_decide_called_name():
    state = InternalState()
    engine = ExpressionEngine(state)
    
    res = engine.decide(phase="responding", cue=SocialCue(user_called_name=True))
    assert res.expression == Expression.EXCITED

def test_decide_comic_moment():
    state = InternalState()
    engine = ExpressionEngine(state)
    
    res = engine.decide(phase="responding", cue=SocialCue(comic_moment=True))
    assert res.expression == Expression.FLUSTERED

def test_validate_proposal():
    state = InternalState()
    engine = ExpressionEngine(state)
    
    assert engine.validate_proposal("happy") == Expression.HAPPY
    assert engine.validate_proposal("PROUD") == Expression.PROUD
    assert engine.validate_proposal("invalid_nonsense") is None
    assert len(engine.rejections) == 1
