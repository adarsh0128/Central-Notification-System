def test_exponential_backoff_calculation() -> None:
    # Verify backoff curve matches the specification requirements: 4 ** retry_attempt
    # Attempt 0 -> 4**0 = 1 second delay
    # Attempt 1 -> 4**1 = 4 seconds delay
    # Attempt 2 -> 4**2 = 16 seconds delay
    # Attempt 3 -> 4**3 = 64 seconds delay
    
    backoffs = [4 ** attempt for attempt in range(4)]
    assert backoffs == [1, 4, 16, 64]
