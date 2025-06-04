import redis
import boto3
import json
import logging


class S3DataFetcher:
    def __init__(self, env, bucket_suffix, file_name):
        self.env = env
        self.file_name = file_name
        self.s3_client = boto3.client('s3')
        # eg: env = 'dev', bucket_suffix = 'supplier-config', file_name = 'disease_vaccine.json'
        self.s3_bucket_name = f"imms-{env}-{bucket_suffix}"

    def load_data(self):
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=self.file_name)
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except Exception as e:
            logging.error(f"Failed to load data from S3: {str(e)}")
            return None

    @staticmethod
    def factory(env, bucket_suffix, file_name):
        """Factory function to create an S3DataFetcher instance."""
        return S3DataFetcher(env, bucket_suffix, file_name)

class RedisDataFetcher:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis = redis.StrictRedis(host=redis_host, port=redis_port, db=0, decode_responses=True)
        
    @staticmethod
    def factory(env, redis_host='localhost', redis_port=6379, s3_bucket_name=None):
        """Factory function to create a DataFetcher instance."""
        
        return DataFetcher(env, redis_host, redis_port, s3_bucket_name)

    def get_data(self, key):
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def set_data(self, key, value):
        self.redis.set(key, json.dumps(value))


class DataFetcher:
    def __init__(self, env, redis_host='localhost', redis_port=6379):
        self.env = env
        self.redis_host = redis_host
        self.redis_port = redis_port

    def load(self, mapping_file):
        redis_cache = RedisDataFetcher.factory(self.env, self.redis_host, self.redis_port)
        mapping_cache = redis_cache.get_data(mapping_file)
        
        if not mapping_cache:
            logging.info(f"Mapping file {mapping_file} not found in Redis, fetching from S3...")
            s3_data_fetcher = S3DataFetcher.factory(self.env, 'supplier-config', mapping_file)
            mapping_cache = s3_data_fetcher.load_data()
            if mapping_cache:
                redis_cache.set_data(mapping_file, mapping_cache)
                logging.info(f"Mapping file {mapping_file} loaded from S3 and saved to Redis.")
            else:
                logging.error(f"Failed to load mapping file {mapping_file} from S3.")
        
        
        # Redis setup
        self.redis = redis.StrictRedis(host=redis_host, port=redis_port, db=0, decode_responses=True)
        
        # S3 setup
        self.s3_client = boto3.client('s3')
        self.s3_bucket_name = s3_bucket_name
        
        # Logging setup for debugging
        logging.basicConfig(level=logging.INFO)
        
    def get_data(self, key):
        # First, try to get the data from Redis
        data = self.redis.get(key)
        
        if data:
            logging.info(f"Data found in Redis for key {key}.")
            return json.loads(data)
        
        # If not in Redis, fetch from S3
        logging.info(f"Data not found in Redis for key {key}, fetching from S3...")
        data = self.fetch_data_from_s3(key)
        
        # Store the data in Redis for future use
        if data:
            self.redis.set(key, json.dumps(data))
            logging.info(f"Data loaded from S3 and saved to Redis for key {key}.")
            return data
        
        logging.error(f"No data found in S3 for key {key}.")
        return None

    def fetch_data_from_s3(self, key):
        try:
            # Assuming the key is the file name in S3
            response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=key)
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except Exception as e:
            logging.error(f"Failed to fetch data from S3: {str(e)}")
            return None
        


def create_data_fetcher(env, redis_host='localhost', redis_port=6379, s3_bucket_name=None):
    """Factory function to create a DataFetcher instance."""
    
    s3_bucket_name = f"imms-{env}-supplier-config"
    
    return DataFetcher(env, redis_host, redis_port, s3_bucket_name)
data_fetcher: DataFetcher = DataFetcher(
    env='dev',  # Example environment, can be 'dev', 'test', 'prod', etc.
    redis_host='localhost',  # Replace with your Redis host
    redis_port=6379,         # Replace with your Redis port
    s3_bucket_name='your_s3_bucket_name'  # Replace with your S3 bucket name
)


# Example Usage:
if __name__ == "__main__":
    # Replace 'your_s3_bucket_name' with your actual S3 bucket name
    fetcher = DataFetcher(redis_host='localhost', redis_port=6379, s3_bucket_name='your_s3_bucket_name')
    
    # Example of how you can use it
    key = "mapping_file.json"  # This is an example, your key could be different
    data = fetcher.get_data(key)
    
    if data:
        print("Data fetched:", data)
    else:
        print("No data found.")
