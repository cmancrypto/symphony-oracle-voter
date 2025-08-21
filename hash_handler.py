import hashlib
def get_aggregate_vote_hash(salt: str, exchange_rates_str: str, validator: str) -> str:
    # Construct the source string
    source_str = f"{salt}:{exchange_rates_str}:{validator}"

    # Create a SHA256 hash object
    hash_object = hashlib.sha256()

    # Update the hash object with the source string (encoded to bytes)
    hash_object.update(source_str.encode('utf-8'))

    # Get the first 20 bytes of the hash (to match tmhash.NewTruncated())
    truncated_hash = hash_object.digest()[:20]

    # Convert the truncated hash to a hexadecimal string
    return truncated_hash.hex()

"""
# Example usage:
salt = "1234"
exchange_rates_str = "8888.0ukrw,1.243uusd,0.99usdr"
voter = "symphonyvaloper1..."  # Replace with actual validator operator address

hash_result = get_aggregate_vote_hash(salt, exchange_rates_str, voter)

"""