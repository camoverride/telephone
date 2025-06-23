from collections import defaultdict, Counter
import pickle
import random



def train_markov_model_with_probs(dataset,
                                  output_path="_model.pkl"):
    """
    
    """
    transitions = defaultdict(Counter)

    # Read the dataset line by line
    with open(dataset, 'r', encoding='utf-8') as f:
        for line in f:
            words = line.strip().split()
            for i in range(len(words) - 1):
                transitions[words[i]][words[i + 1]] += 1

    # Normalize counts into probabilities
    model = {}
    for word, counter in transitions.items():
        total = sum(counter.values())
        model[word] = {next_word: count / total for next_word, count in counter.items()}

    # Save the model
    with open(output_path, 'wb') as f:
        pickle.dump(model, f)

    return output_path


def load_model(filename):
    """
    
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)


def weighted_sample(prob_dict):
    """
    
    """
    r = random.random()
    cumulative = 0.0
    for word, prob in prob_dict.items():
        cumulative += prob
        if r <= cumulative:
            return word
    # Fallback (should rarely happen due to float precision)
    return random.choice(list(prob_dict))


def generate_text(model,
                  start_word,
                  length=20):
    """
    
    """
    word = start_word
    output = [word]

    for _ in range(length - 1):
        if word not in model:
            break
        word = weighted_sample(model[word])
        output.append(word)

    return " ".join(output)



if __name__ == "__main__":

    dataset_path = "markov_data.txt"
    model_path = "_model.pkl"

    # Train and save model
    trained_model_path = train_markov_model_with_probs(dataset_path, model_path)

    # Load model
    loaded_model = load_model(trained_model_path)

    # Generate and print text
    text = generate_text(loaded_model,
                         start_word="one",
                         length=30)
    print(text)
