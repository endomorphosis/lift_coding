"""Tests for API key authentication and management."""

import uuid

import pytest

from handsfree.db.api_keys import (
    create_api_key,
    delete_api_key,
    generate_api_key,
    get_api_key,
    get_api_keys_by_user,
    hash_api_key,
    revoke_api_key,
    validate_api_key,
)
from handsfree.db.connection import init_db


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    return init_db(":memory:")


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return str(uuid.uuid4())


class TestApiKeyGeneration:
    """Test API key generation and hashing."""

    def test_generate_api_key_length(self):
        """Test that generated API keys have the expected length."""
        key = generate_api_key()
        assert len(key) == 43  # URL-safe base64 encoding of 32 bytes

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100  # All keys should be unique

    def test_hash_api_key(self):
        """Test that API key hashing is consistent."""
        key = "test-key-12345"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex characters

    def test_hash_api_key_different_keys(self):
        """Test that different keys produce different hashes."""
        hash1 = hash_api_key("key1")
        hash2 = hash_api_key("key2")
        assert hash1 != hash2


class TestApiKeyCreation:
    """Test API key creation."""

    def test_create_api_key_without_label(self, db, test_user_id):
        """Test creating an API key without a label."""
        plaintext_key, api_key = create_api_key(db, test_user_id)

        assert plaintext_key is not None
        assert len(plaintext_key) == 43
        assert api_key.id is not None
        assert api_key.user_id == test_user_id
        assert api_key.label is None
        assert api_key.key_hash == hash_api_key(plaintext_key)
        assert api_key.created_at is not None
        assert api_key.revoked_at is None
        assert api_key.last_used_at is None

    def test_create_api_key_with_label(self, db, test_user_id):
        """Test creating an API key with a label."""
        label = "Mobile app"
        plaintext_key, api_key = create_api_key(db, test_user_id, label=label)

        assert api_key.label == label

    def test_create_multiple_keys_for_user(self, db, test_user_id):
        """Test creating multiple API keys for the same user."""
        key1, _ = create_api_key(db, test_user_id, label="Key 1")
        key2, _ = create_api_key(db, test_user_id, label="Key 2")

        assert key1 != key2

        keys = get_api_keys_by_user(db, test_user_id)
        assert len(keys) == 2


class TestApiKeyValidation:
    """Test API key validation."""

    def test_validate_valid_key(self, db, test_user_id):
        """Test validating a valid API key."""
        plaintext_key, api_key = create_api_key(db, test_user_id)

        validated_user_id = validate_api_key(db, plaintext_key)
        assert validated_user_id == test_user_id

    def test_validate_invalid_key(self, db):
        """Test validating an invalid API key."""
        result = validate_api_key(db, "invalid-key-12345")
        assert result is None

    def test_validate_revoked_key(self, db, test_user_id):
        """Test that revoked keys cannot be validated."""
        plaintext_key, api_key = create_api_key(db, test_user_id)

        # Revoke the key
        revoke_api_key(db, api_key.id)

        # Try to validate it
        result = validate_api_key(db, plaintext_key)
        assert result is None

    def test_validate_key_updates_last_used(self, db, test_user_id):
        """Test that validating a key updates last_used_at."""
        plaintext_key, api_key = create_api_key(db, test_user_id)

        # Initial last_used_at should be None
        assert api_key.last_used_at is None

        # Validate the key
        validate_api_key(db, plaintext_key)

        # Check that last_used_at was updated
        updated_key = get_api_key(db, api_key.id)
        assert updated_key.last_used_at is not None
        assert updated_key.last_used_at > api_key.created_at


class TestApiKeyRetrieval:
    """Test API key retrieval functions."""

    def test_get_api_key_by_id(self, db, test_user_id):
        """Test retrieving an API key by ID."""
        _, api_key = create_api_key(db, test_user_id, label="Test")

        retrieved = get_api_key(db, api_key.id)
        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.user_id == test_user_id
        assert retrieved.label == "Test"

    def test_get_nonexistent_api_key(self, db):
        """Test retrieving a nonexistent API key."""
        result = get_api_key(db, str(uuid.uuid4()))
        assert result is None

    def test_get_api_keys_by_user_empty(self, db, test_user_id):
        """Test listing keys for a user with no keys."""
        keys = get_api_keys_by_user(db, test_user_id)
        assert keys == []

    def test_get_api_keys_by_user_multiple(self, db, test_user_id):
        """Test listing multiple keys for a user."""
        create_api_key(db, test_user_id, label="Key 1")
        create_api_key(db, test_user_id, label="Key 2")
        create_api_key(db, test_user_id, label="Key 3")

        keys = get_api_keys_by_user(db, test_user_id)
        assert len(keys) == 3
        # Should be ordered by created_at DESC
        assert keys[0].label == "Key 3"

    def test_get_api_keys_by_user_excludes_revoked(self, db, test_user_id):
        """Test that revoked keys are excluded by default."""
        _, key1 = create_api_key(db, test_user_id, label="Active")
        _, key2 = create_api_key(db, test_user_id, label="Revoked")
        revoke_api_key(db, key2.id)

        keys = get_api_keys_by_user(db, test_user_id, include_revoked=False)
        assert len(keys) == 1
        assert keys[0].label == "Active"

    def test_get_api_keys_by_user_includes_revoked(self, db, test_user_id):
        """Test that revoked keys can be included."""
        create_api_key(db, test_user_id, label="Active")
        _, key2 = create_api_key(db, test_user_id, label="Revoked")
        revoke_api_key(db, key2.id)

        keys = get_api_keys_by_user(db, test_user_id, include_revoked=True)
        assert len(keys) == 2

    def test_get_api_keys_isolated_by_user(self, db):
        """Test that keys are isolated by user."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        create_api_key(db, user1_id, label="User 1 Key")
        create_api_key(db, user2_id, label="User 2 Key")

        user1_keys = get_api_keys_by_user(db, user1_id)
        user2_keys = get_api_keys_by_user(db, user2_id)

        assert len(user1_keys) == 1
        assert len(user2_keys) == 1
        assert user1_keys[0].label == "User 1 Key"
        assert user2_keys[0].label == "User 2 Key"


class TestApiKeyRevocation:
    """Test API key revocation."""

    def test_revoke_api_key(self, db, test_user_id):
        """Test revoking an API key."""
        _, api_key = create_api_key(db, test_user_id)

        revoked = revoke_api_key(db, api_key.id)
        assert revoked is not None
        assert revoked.revoked_at is not None
        assert revoked.revoked_at > api_key.created_at

    def test_revoke_nonexistent_key(self, db):
        """Test revoking a nonexistent key."""
        result = revoke_api_key(db, str(uuid.uuid4()))
        assert result is None

    def test_revoke_already_revoked_key(self, db, test_user_id):
        """Test revoking an already revoked key."""
        _, api_key = create_api_key(db, test_user_id)

        # Revoke once
        first_revoked = revoke_api_key(db, api_key.id)
        first_revoked_at = first_revoked.revoked_at

        # Try to revoke again
        second_revoked = revoke_api_key(db, api_key.id)
        # The revoked_at timestamp should be updated
        assert second_revoked.revoked_at >= first_revoked_at


class TestApiKeyDeletion:
    """Test API key deletion."""

    def test_delete_api_key(self, db, test_user_id):
        """Test deleting an API key."""
        _, api_key = create_api_key(db, test_user_id)

        result = delete_api_key(db, api_key.id)
        assert result is True

        # Verify it's gone
        retrieved = get_api_key(db, api_key.id)
        assert retrieved is None

    def test_delete_nonexistent_key(self, db):
        """Test deleting a nonexistent key."""
        result = delete_api_key(db, str(uuid.uuid4()))
        assert result is False


class TestApiKeySecurity:
    """Test security aspects of API key handling."""

    def test_key_hash_stored_not_plaintext(self, db, test_user_id):
        """Test that only the hash is stored, not the plaintext key."""
        plaintext_key, api_key = create_api_key(db, test_user_id)

        # Retrieve the key from the database
        retrieved = get_api_key(db, api_key.id)

        # Verify the plaintext key is NOT in the hash
        assert plaintext_key not in retrieved.key_hash
        # Verify the hash is correct
        assert retrieved.key_hash == hash_api_key(plaintext_key)

    def test_different_keys_same_user(self, db, test_user_id):
        """Test that different keys for the same user have different hashes."""
        key1, api_key1 = create_api_key(db, test_user_id)
        key2, api_key2 = create_api_key(db, test_user_id)

        assert key1 != key2
        assert api_key1.key_hash != api_key2.key_hash
