from je_load_density import execute_action


# test_list = [
#     ["loading_test_with_user", {"user_detail_dict": {
#         "request_method": "get",
#         "request_url": "http://httpbin.org/get"
#     },
#         "user_count": 50, "spawn_rate": 10, "test_time": 10}
#      ]
# ]
# [
#     ["what function we want to use", {"user setting dict":{
#         "request_method": "what http method",
#         "request_url": "test url"
#     },
#          "user_count": 50, "spawn_rate": 10, "test_time": 10}
#     ]
# ]

test_list = [
    ["loading_test_with_user", {"user_detail_dict": {
        "request_method": "get",
        "request_url": "http://httpbin.org/get"
    },
        "user_count": 50, "spawn_rate": 10, "test_time": 10}
     ],
    ["generate_html"]
]

print(execute_action(test_list))
