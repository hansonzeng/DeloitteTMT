# file for association rules recovery
import pandas as pd
from watson_developer_cloud import VisualRecognitionV3

'''
Get image classification using our custom classifier
'''

# call this function by providing a URL to an image and can optionally update the API key
def classify(images_file, classifier, min_score, image_url=None, api_key="72468179b79518522ff0c2d981522827378c8dd4"):
    # API Setup
    visual_recognition = VisualRecognitionV3('2016-05-20', api_key=api_key)

    if image_url is not None:
        # Get results by calling API
        results = visual_recognition.classify(images_url=image_url, classifier_ids=classifier)
    else:
        results = visual_recognition.classify(images_file=images_file, classifier_ids=classifier)

    list_of_positives = []
    for x in results['images'][0]['classifiers'][0]['classes']:

        # Make a decision and add to list if positive
        score = float(x['score'])
        if score > min_score:  # Would be better if we could compare relative scores
            list_of_positives.append(str(x['class']))

    return list_of_positives


# currently only built for single item item sets
def lookup(lookup_value, rules_to_return=1):
    # read in lookup table - could make this dynamic or a variable but simplifying for demo
    lookup_table = pd.read_csv('single_a_filtered.csv')

    # get list of all antecedents
    antes = list(set(lookup_table['str_a']))

    # check if lookup value is in antecedents
    if lookup_value in antes:
        # look up single interest rules that match the lookup value
        rules = lookup_table.loc[lookup_table['str_a'] == lookup_value]

        # sort rules by lift
        sorted_rules = rules.sort_values('lift', ascending=False)

        # return the top X rules
        return sorted_rules.head(rules_to_return)

    else:
        print
        "no matching lookup values"
        return "no value found"