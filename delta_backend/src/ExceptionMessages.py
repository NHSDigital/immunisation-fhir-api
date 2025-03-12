# all exceptions and messgaes
UNEXPECTED_EXCEPTION = 0
VALUE_CHECK_FAILED = 1
HEADER_CHECK_FAILED = 2
RECORD_LENGTH_CHECK_FAILED = 3
VALUE_PREDICATE_FALSE = 4
RECORD_CHECK_FAILED = 5
RECORD_PREDICATE_FALSE = 6
UNIQUE_CHECK_FAILED = 7
ASSERT_CHECK_FAILED = 8
FINALLY_ASSERT_CHECK_FAILED = 9
PARSING_ERROR = 10


MESSAGES = {
                UNEXPECTED_EXCEPTION: 'Unexpected exception [%s]: %s',
                VALUE_CHECK_FAILED: 'Value check failed.',
                HEADER_CHECK_FAILED: 'Header check failed.',
                RECORD_LENGTH_CHECK_FAILED: 'Record length check failed.',
                RECORD_CHECK_FAILED: 'Record check failed.',
                VALUE_PREDICATE_FALSE: 'Value predicate returned false.',
                RECORD_PREDICATE_FALSE: 'Record predicate returned false.',
                UNIQUE_CHECK_FAILED: 'Unique check failed.',
                ASSERT_CHECK_FAILED: 'Assertion check failed.',
                FINALLY_ASSERT_CHECK_FAILED: 'Final assertion check failed.',
                PARSING_ERROR : 'Failed to parse data correctly.'
            }