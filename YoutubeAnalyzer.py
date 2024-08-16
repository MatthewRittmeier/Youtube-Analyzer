from googleapiclient.discovery import build
from PIL import Image
import os, shutil
import requests
import json
import random
import webcolors
import time

api_key = 'AIzaSyBNp4NetZmqY791wFPD2AvbhVP9Scs3rh8'
youtube = build('youtube', 'v3', developerKey=api_key)
imgFolder = 'Images/'
JSONFolder = 'JSON Data/'
analysisFolder = 'Finished analysis/'

def QueryUser():
    # Real code - Api request
    prompt = input("Enter search term to analyze. To do multiple for a better analysis, seperate each search term with a '|': ")
    maxResults = input("Enter the maximum amount of results that should be returned (capped at 50): ")

    if maxResults == "" or int(maxResults) > 50:
        print('Clamped to 50 results')
        maxResults = "50"
        
    minimumTagUseCount = input("Enter the minimum amount of times a tag or word has to be used before considering it in data analysis... \n(<2 to keep all, 2 to remove uncommon, any more to your liking): ")

    if minimumTagUseCount == "":
        minimumTagUseCount = int(0)
        
    fileName = input("File name: ")

    # Delete images first?
    if input("Clear previous analysis first? y/n?: ") == 'y':
        for filename in os.listdir(imgFolder):
            file_path = os.path.join(imgFolder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
        for filename in os.listdir(JSONFolder):
            file_path = os.path.join(JSONFolder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
    
    return (prompt, maxResults, minimumTagUseCount, fileName)

def DownloadYoutubeData(searchTerm, maxResults, minimumTagUseCount):
    # Make API request        
    request = youtube.search().list(
        q=searchTerm,
        part='id, snippet',
        maxResults=maxResults,
        type='video',
    )

    # Temp variables
    response = request.execute()
    videos = []
    
    # Save response data
    for search_result in response.get('items', []):
            
        # Save video data
        video_url = 'https://www.youtube.com/watch?v=' + search_result['id']['videoId']
        channel_url = 'https://www.youtube.com/channel/' + search_result['snippet']['channelId']
        image_url = search_result['snippet']['thumbnails']['high']['url']
        videos.append(search_result['id']['videoId'])
        
        # File dir
        file_dir = imgFolder + search_result['id']['videoId'] + '.jpeg'
        
        # Change image save location
        directory = os.path.dirname(file_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Save image file
        img_data = requests.get(image_url).content
        with open(file_dir, 'wb') as handler:
            handler.write(img_data)
            
        # Active console visualization
        print('Video Title: ' + search_result['snippet']['title'])
        print('Video URL: ' + video_url)
        print('Channel URL: ' + channel_url)

    # Seperate video ids into string split list
    promptString = ""
    for videoAtIdx in  videos:
        promptString = promptString + "," + videoAtIdx
    promptString = promptString[1:]

    # Request make
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=promptString,
    ).execute()

    # Create and save JSON data that will be used
    for search_result in request.get('items', []):    
        # File dir
        file_dir = JSONFolder + search_result['id'] + '.json'
        
        # Change Json save location
        directory = os.path.dirname(file_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Attempt to get data (data doesnt always return)
        try:
            tags = search_result['snippet']['tags'][0],
        except Exception:
            tags = []
            
        try:
            viewCount = int(search_result['statistics']['viewCount'])
        except Exception:
            viewCount = null
            
        try:
            likeCount = int(search_result['statistics']['likeCount'])
        except Exception:
            likeCount = int(0)
            
        try:
            commentCount = int(search_result['statistics']['commentCount'])
        except Exception:
            commentCount = int(0)
            
        # Json format
        data = {
            "videoDetails":{
                "VideoLink": 'https://www.youtube.com/watch?v=' + search_result['id'],
                "ChannelLink": 'https://www.youtube.com/channel/' + search_result['snippet']['channelId'],
                "VideoId": search_result['id'],
                "ChannelId": search_result['snippet']['channelId'],
                "Title": search_result['snippet']['title'].translate({ord(i): None for i in '()[]-_+=<>/`~'}),
                "ChannelName": search_result['snippet']['channelTitle'],
                "Description": search_result['snippet']['description'],
            },
            
            "stats":{
                "ViewCount": viewCount,
                "LikeCount": likeCount,
                "CommentCount": commentCount,
                "Like2ViewRatio": likeCount / viewCount,
                "Comment2ViewRatio": commentCount / viewCount,
                "Tags": tags,
            }
        }
        
        print(data)
        
        # Save file
        save_file = open(file_dir, "w")  
        json.dump(data, save_file, indent = 6)  
        save_file.close()   
        print(promptString)
        
    # Close
    youtube.close()

def AnalyzeYoutubeData():
    Words, WordCounts, WordScores, Tags, TagCounts, TagScores = AnalyzeTextAndTags()
    AnalyzeImages()
    
    # Contruct return data
    data = {
        "SortedWordsInTitle": Words,
        "SortedWordCountsInTitle": WordCounts,
        "SortedScoringForWords": WordScores,
        
        "SortedTags": Tags,
        "SortedTagCounts": TagCounts,
        "SortedScoringForTags": TagScores,
    }
    
    print(data)
    return data

def AnalyzeTextAndTags():
    # Setup variables
    Words = []
    WordCounts = []
    WordScores = []
    
    Tags = []
    TagCounts = []
    TagScores = []
    
    # Word and Tag analysis
    for dir, sub, files in os.walk(JSONFolder):
        for data in files:
            
            # Load data for processing
            print(data)
            data = json.load(open(dir + data))
            
            # Set scoring multiplier
            ScoreMultiplier = data['stats']['ViewCount'] * data['stats']['Like2ViewRatio']
            
            # Slice title into a list of words
            list = str(data['videoDetails']['Title']).split()
            
            # Analyze terms used in the titles
            for word in list:
                if word not in Words:
                    Words.append(word)
                    WordCounts.append(1)
                    WordScores.append(ScoreMultiplier)
                else:
                    index = Words.index(word)
                    WordCounts[index] = WordCounts[index] + 1
                    WordScores[index] += ScoreMultiplier
            
            for tag in data['stats']['Tags']:
                if tag not in Tags:
                    Tags.append(tag)
                    TagCounts.append(1)
                    TagScores.append(ScoreMultiplier)
                else:
                    index = Tags.index(tag)
                    TagCounts[index] = TagCounts[index] + 1
                    TagScores[index] += ScoreMultiplier
                    
            print(Words, WordCounts)
            print(Tags, TagCounts)
            
    Words = [x for _, x in sorted(zip(WordCounts, Words))]
    WordScores = [x for _, x in sorted(zip(WordCounts, WordScores))]
    WordCounts.sort()
    Tags = [x for _, x in sorted(zip(TagCounts, Tags))]
    TagScores = [x for _, x in sorted(zip(TagCounts, TagScores))]
    TagCounts.sort()
    
    print(Words, WordCounts)
    
    # Remove tags with low numbers
    while True and len(Words) > 10:
        if (WordCounts[0] < int(minimumTagsUseCount)):
            WordCounts.pop(0)
            Words.pop(0)
        else:
            break
    while True and len(Tags) > 10:
        if (TagCounts[0] < 1):
            TagCounts.pop(0)
            Tags.pop(0)
        else:
            break
    
    
    
    # Reverse order for human readability.
    Words.reverse()
    WordCounts.reverse()
    WordScores.reverse()
    Tags.reverse()
    TagCounts.reverse()
    TagScores.reverse()
    
    print(Words, WordCounts)
    print(Tags, TagCounts)
    
    return Words, WordCounts, WordScores, Tags, TagCounts, TagScores

def AnalyzeImages():
    print("Preparing image scans. See you in a while ;)")
    time.sleep(0)
    
    # Lasting variables
    Colors = []
    ColorCounts = []
    ColorScores = []
    
    # Loop through images
    for dir, sub, files in os.walk(imgFolder):
        for file in files:
            print (imgFolder + file)
            im = Image.open(imgFolder + file, 'r')
            pixels = list(im.getdata())
            width, height = im.size
            pixels = [pixels[i * width:(i + 1) * width] for i in range(height)]
            
            for pixelArray in pixels:
                for pixel in pixelArray:
                    print(pixel)
                    colorName = webcolors.hex_to_name(pixel)
                    
                    if colorName not in Colors:
                        Colors.append(colorName)
                        ColorCounts.append(1)
                        #ColorScores.append("Nothing for now, just remember to do it later")
                    else:
                        index = Colors.index(colorName)
                        ColorCounts[index] += 1
                        
            print("ioudfiuoergiuowergoiweriwerliweoiweoiweoreoewoweoweobwoweouweoweoiweobiwobiew")

def SaveAnalysisResults(fileName, results):
    # File dir
    file_dir = analysisFolder + fileName + '.json'
        
    # Change Json save location
    directory = os.path.dirname(file_dir)
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    # Create and write file
    f = open(file_dir, 'w')
    json.dump(data, f, indent = 6)  
    f.close()

# Main
if __name__ == "__main__":
    prompt, maxResults, minimumTagsUseCount, fileName = QueryUser()
    splitPrompt = prompt.split('|')
    
    for searchTerm in splitPrompt:
        DownloadYoutubeData(searchTerm, maxResults, minimumTagsUseCount)
        
    data = AnalyzeYoutubeData()
    SaveAnalysisResults(fileName, data)