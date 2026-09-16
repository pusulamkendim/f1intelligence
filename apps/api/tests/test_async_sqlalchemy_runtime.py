def test_greenlet_is_available_for_sqlalchemy_asyncio() -> None:
    import greenlet

    assert greenlet.__version__
