import { DynamoDB } from 'aws-sdk';

const dynamoDB = new DynamoDB.DocumentClient();

export const handler = async (event: any): Promise<any> => {
  const operation = event.httpMethod;
  const dynamoDBTableName = process.env.DYNAMODB_TABLE_NAME || 'DefaultTableName';

  if (event.path === '/_status' && operation === 'GET') {
    const statusResponse = {
      status: 'healthy',
      message: 'Backend is up and running.',
    };
    return {
      statusCode: 200,
      body: JSON.stringify(statusResponse),
    };
  }
  
  if (operation === 'POST') {
    // Handle the POST request to create a new item
    const params = {
      TableName: dynamoDBTableName,
      Item: JSON.parse(event.body),
    };

    try {
      await dynamoDB.put(params).promise();
      return {
        statusCode: 201,
        body: JSON.stringify('Item created successfully.'),
      };
    } catch (error) {
      console.error('Error:', error); // Log the error
      return {
        statusCode: 500,
        body: JSON.stringify('Error creating the item.'),
      };
    }
  } else if (operation === 'GET') {
    // Handle the GET request to retrieve an item
    const params = {
      TableName: dynamoDBTableName,
      Key: {
        id: event.queryStringParameters.id,
      },
    };

    try {
      const data = await dynamoDB.get(params).promise();
      if (!data.Item) {
        // Item not found, return an error response
        return {
          statusCode: 404,
          body: JSON.stringify('Item not found.'),
        };
      }
      return {
        statusCode: 200,
        body: JSON.stringify(data.Item),
      };
    } catch (error) {
      console.error('Error:', error); // Log the error
      return {
        statusCode: 500,
        body: JSON.stringify('Error retrieving the item.'),
      };
    }
  } else if (operation === 'DELETE') {
    // Handle the DELETE request to delete an item
    const params = {
      TableName: dynamoDBTableName,
      Key: {
        id: event.queryStringParameters.id,
      },
    };

    try {
        const data = await dynamoDB.get(params).promise();
        if (!data.Item) {
            // Item not found, return an error response
            return {
              statusCode: 404,
              body: JSON.stringify('Item not found.'),
            };
          }
    
          await dynamoDB.delete(params).promise();
          return {
            statusCode: 200,
            body: JSON.stringify('Item deleted successfully.'),
          };
    } catch (error) {
      console.error('Error:', error); // Log the error
      return {
        statusCode: 500,
        body: JSON.stringify('Error deleting the item.'),
      };
    }
  }

  return {
    statusCode: 400,
    body: JSON.stringify('Invalid operation.'),
  };
};
