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

# Set settings folder
settingsFile = "settings.json"

settings = json.load(open(settingsFile))
ColorSimplifierFactor = settings["ColorSimplifierFactor"]
OpenImagesOnProcess = settings["OpenImagesOnProcess"]

def QueryUser():
    # Real code - Api request
    prompt = input("Enter search term to analyze. To do multiple for a better analysis, seperate each search term with a '|': ")
    if prompt == "":
        raise Exception("No search term specified")
    
    maxResults = input("Enter the maximum amount of results that should be returned (capped at 50): ")

    if maxResults == "" or int(maxResults) > 50:
        print('Clamped to 50 results')
        maxResults = "50"
        
    minimumTagUseCount = input("Enter the minimum amount of times a tag or word has to be used before considering it in data analysis... \n(<2 to keep all, 2 to remove uncommon, any more to your liking): ")

    if minimumTagUseCount == "":
        minimumTagUseCount = int(0)
        
    minimumWordUseCount = input("Same as last prompt, but instead with words in the title of a video. Input the minimum amount of times a word in the title has to appear before being considered in analysis: ")

    if minimumWordUseCount == "":
        minimumWordUseCount = int(0)
        
    minimumColorUseCount = input("Same as last prompt, but instead with colors. Input the minimum amount of times a color has to appear before being considered in analysis: ")
        
    if minimumColorUseCount == "":
        minimumColorUseCount = int(0)
        
        
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
    
    return (prompt, maxResults, int(minimumTagUseCount), fileName, int(minimumColorUseCount), int(minimumWordUseCount))

def DownloadYoutubeData(searchTerm, maxResults):
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

def AnalyzeYoutubeData(minimumTagUseCount, minimumWordUseCount, minimumColorUseCount):
    Words, WordCounts, WordScores, Tags, TagCounts, TagScores = AnalyzeTextAndTags(minimumTagUseCount, minimumWordUseCount)
    Colors, ColorCounts, ColorScores = AnalyzeImages(minimumColorUseCount)
    
    # Contruct return data
    data = {
        "SortedWordsInTitle": Words,
        "SortedWordCountsInTitle": WordCounts,
        "SortedScoringForWords": WordScores,
        
        "SortedTags": Tags,
        "SortedTagCounts": TagCounts,
        "SortedScoringForTags": TagScores,
        
        "SortedColors": Colors,
        "SortedColorCounts": ColorCounts,
        "SortedColorScores": ColorScores, 
    }
    
    print(data)
    return data

def AnalyzeTextAndTags(minimumTagUseCount, minimumWordUseCount):
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
        if (WordCounts[0] < int(minimumWordUseCount)):
            WordCounts.pop(0)
            Words.pop(0)
            WordScores.pop(0)
        else:
            break
    while True and len(Tags) > 10:
        if (TagCounts[0] < minimumTagUseCount):
            TagCounts.pop(0)
            Tags.pop(0)
            TagScores.pop(0)
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

def AnalyzeImages(minimumColorUseCount):
    print("Preparing image scans. See you in a while ;)")
    
    ScoreMultiplierList = []
    for dir, sub, files in os.walk(JSONFolder):
        for data in files:
            
            # Load data for processing
            data = json.load(open(dir + data))
            
            # Set scoring multiplier
            ScoreMultiplierList.append(data['stats']['ViewCount'] * data['stats']['Like2ViewRatio'])
    
    print(ScoreMultiplierList)
    time.sleep(3)
    
    # Lasting variables
    Colors = []
    ColorCounts = []
    ColorScores = []
    
    # Loop through images
    for dir, sub, files in os.walk(imgFolder):
        for file in files:
            print (imgFolder + file)
            
            ScoreMultiplier = ScoreMultiplierList[files.index(file)]
            im = Image.open(imgFolder + file, 'r')
            if OpenImagesOnProcess:
                im.show()
            pixels = list(im.getdata())
            
            for pixel in pixels:
                # Simplify the color 
                simplifiedPixel = (pixel[0] / ColorSimplifierFactor, pixel[1] / ColorSimplifierFactor, pixel[2] / ColorSimplifierFactor)
                simplifiedPixel = (round(simplifiedPixel[0]), round(simplifiedPixel[1]), round(simplifiedPixel[2]))
                simplifiedPixel = (simplifiedPixel[0] * ColorSimplifierFactor, simplifiedPixel[1] * ColorSimplifierFactor, simplifiedPixel[2] * ColorSimplifierFactor)
                simplifiedPixel = str(simplifiedPixel)
                
                print(simplifiedPixel, pixel)
                
                if simplifiedPixel not in Colors:
                    Colors.append(simplifiedPixel)
                    ColorCounts.append(1)
                    ColorScores.append(ScoreMultiplier)
                else:
                    index = Colors.index(simplifiedPixel)
                    ColorCounts[index] += 1
                    ColorScores[index] += ScoreMultiplier
                       
            print("Image " + str(files.index(file) + 1) + " out of " + str(len(files)) + " done processing. Proceeding to the next image.")
            time.sleep(2)
            print(Colors, ColorCounts, ColorScores)
           
    # Sort 
    Colors = [x for _, x in sorted(zip(ColorCounts, Colors))]
    ColorScores = [x for _, x in sorted(zip(ColorCounts, ColorScores))]
    ColorCounts.sort()
            
    # Remove tags with low numbers
    while True and len(Colors) > 10:
        if (ColorCounts[0] < int(minimumColorUseCount)):
            ColorCounts.pop(0)
            Colors.pop(0)
            ColorScores.pop(0)
        else:
            break
        
    Colors.reverse()
    ColorCounts.reverse()
    ColorScores.reverse()
    
    return (Colors, ColorCounts, ColorScores)

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
    prompt, maxResults, minimumTagUseCount, fileName, minimumColorUseCount, minimumWordUseCount = QueryUser()
    splitPrompt = prompt.split('|')
    
    for searchTerm in splitPrompt:
        DownloadYoutubeData(searchTerm, maxResults)
        
    data = AnalyzeYoutubeData(minimumTagUseCount, minimumWordUseCount, minimumColorUseCount)
    SaveAnalysisResults(fileName, data)