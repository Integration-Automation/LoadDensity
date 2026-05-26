"""
GraphQL recipe: compose a GraphQL query into a fast_http_user task.
"""

from je_load_density import graphql_to_http_task, start_test


def main() -> None:
    query = """
    query GetUser($id: ID!) {
      user(id: $id) { id name email }
    }
    """
    task = graphql_to_http_task(
        endpoint="${var.base}/graphql",
        query=query,
        variables={"id": "${var.user_id}"},
        operation_name="GetUser",
        headers={"Authorization": "Bearer ${var.token}"},
        assertions=[{"type": "status_code", "value": 200}],
        extract=[{"var": "user_name",
                  "from": "json_path", "path": "data.user.name"}],
    )

    start_test(
        user_detail_dict={"user": "fast_http_user"},
        user_count=10, spawn_rate=5, test_time=30,
        variables={"base": "https://api.example.com",
                   "user_id": "42",
                   "token": "rotate-me"},
        tasks=[task],
    )


if __name__ == "__main__":
    main()
