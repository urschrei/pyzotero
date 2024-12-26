import json

def find_outermost_tuples(tuples):
    tuples = sorted(tuples, key=lambda x: x[0])
    outermost_tuples = []

    for current in tuples:
        if not outermost_tuples or current[0] > outermost_tuples[-1][1]:
            outermost_tuples.append(current)
        else:
            outermost_tuples[-1] = (
                min(outermost_tuples[-1][0], current[0]),
                max(outermost_tuples[-1][1], current[1])
            )
    return outermost_tuples

def find_bracket_pairs(s):
    stack = []
    pairs = []
    for i, char in enumerate(s):
        if char == '[':
            stack.append(i)  
        elif char == ']':
            if stack:
                left_index = stack.pop()  
                pairs.append((left_index, i)) 
    if stack:
        print("Unmatched brackets found")
    return pairs

def find_brace_pairs(s):
    stack = []
    pairs = []
    for i, char in enumerate(s):
        if char == '{':
            stack.append(i) 
        elif char == '}':
            if stack:
                left_index = stack.pop() 
                pairs.append((left_index, i)) 
    if stack:
        print("Unmatched brackets found")
    return pairs

def postprocess_data(input_string):
    result_list_bracket = find_bracket_pairs(input_string)
    result_list_bracket = find_outermost_tuples(result_list_bracket)
    result_list_brace = find_brace_pairs(input_string)
    result_list_brace = find_outermost_tuples(result_list_brace)
    result = max(result_list_brace+result_list_bracket, key=lambda x: x[1] - x[0])
    start_index = result[0]
    end_index = result[1]+1
    json_content = input_string[start_index:end_index]
    data_list = json.loads(json_content)
    return data_list