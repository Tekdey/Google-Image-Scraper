# -*- coding: utf-8 -*-
"""
Created on Sun Jul 12 11:02:06 2020

@author: OHyic

"""
#Import libraries
import os
import concurrent.futures
from GoogleImageScraper import GoogleImageScraper
from patch import webdriver_executable


def worker_thread(search_key):
    image_scraper = GoogleImageScraper(
        webdriver_path,
        image_path,
        search_key,
        number_of_images,
        headless,
        min_resolution,
        max_resolution,
        max_missed,
        user_data_dir=user_data_dir,
        debugger_address=debugger_address)
    image_urls = image_scraper.find_image_urls()
    image_scraper.save_images(image_urls, keep_filenames)

    #Release resources
    del image_scraper

if __name__ == "__main__":
    #Define file path
    webdriver_path = os.path.normpath(os.path.join(os.getcwd(), 'webdriver', webdriver_executable()))
    image_path = os.path.normpath(os.path.join(os.getcwd(), 'photos'))
    # Dedicated throwaway Chrome profile. Never log in to a real Google account from this profile.
    user_data_dir = os.path.normpath(os.path.join(os.getcwd(), 'chrome-profile'))
    # Set to "127.0.0.1:9222" to attach to a pre-launched Chrome (started with --remote-debugging-port=9222).
    # When set, captcha solved once manually stays valid across all subsequent runs.
    # When None, scraper launches its own Chrome using user_data_dir above.
    debugger_address = None

    #Add new search key into array ["cat","t-shirt","apple","orange","pear","fish"]
    search_keys = list(set(["car","stars"]))

    #Parameters
    number_of_images = 10                # Desired number of images
    headless = False                    # True = No Chrome GUI (required on VPS)
    min_resolution = (0, 0)             # Minimum desired image resolution
    max_resolution = (9999, 9999)       # Maximum desired image resolution
    max_missed = 10                     # Max number of failed images before exit
    number_of_workers = 1               # Number of "workers" used. Keep at 1 when sharing one Chrome profile.
    keep_filenames = False              # Keep original URL image filenames

    #Run each search_key in a separate thread
    #Automatically waits for all threads to finish
    #Removes duplicate strings from search_keys
    with concurrent.futures.ThreadPoolExecutor(max_workers=number_of_workers) as executor:
        executor.map(worker_thread, search_keys)
