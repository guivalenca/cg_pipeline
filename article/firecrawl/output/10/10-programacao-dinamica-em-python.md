---
id: "10"
title: "Programação Dinâmica em Python"
source_url: "https://www.geeksforgeeks.org/word-break-problem-dp-32/"
fetch_url: "https://www.geeksforgeeks.org/word-break-problem-dp-32"
resolved_url: "https://www.geeksforgeeks.org/dsa/word-break-problem-dp-32/"
firecrawl_title: "Word Break - GeeksforGeeks"
description: "Your All-in-One Learning Portal: GeeksforGeeks is a comprehensive educational platform that empowers learners across domains-spanning computer science and programming, school education, upskilling, commerce, software tools, competitive exams, and more., Your All-in-One Learning Portal. It contains well written, well thought and well explained computer science and programming articles, quizzes and practice/competitive programming/company interview Questions."
fetched_at: "2026-05-12T03:59:51.232378Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "053d7ef87347c6696250a580eb18f75829eef1e380b68d9b1866546dd2c04c25"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 593
char_count: 4093
content_sha256: "1928838bbf075d3de120ba6cea23c839b83bc1fc33004945e7a0469ce2e0ad8b"
image_count: 13
link_count: 57
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "template_heavy_preserve_code_blocks"
---

# Word Break

Last Updated : 23 Jul, 2025

Given a string **s** and a dictionary of **n** words **dictionary**, check if `s` can be segmented into a sequence of valid words from the dictionary, separated by spaces.

**Examples:**

> **Input:** s= "ilike", dictionary[] = ["i", "like", "gfg"]  
> **Output:** true  
> **Explanation:** The string can be segmented as "i like".  
> **Input:** s= "ilikegfg", dictionary[] = ["i", "like", "man", "india", "gfg"]  
> **Output:** true  
> **Explanation:** The string can be segmented as "i like gfg".  
> **Input:** s= "ilikemangoes", dictionary = ["i", "like", "gfg"]  
> **Output:** false  
> **Explanation:** The string cannot be segmented.

### **[Naive Approach] Using Recursion - O(2^n) Time and O(n) Space**

> The idea is to consider each prefix and search for it in the dictionary. If the prefix is present in the dictionary, we recur for the rest of the string (or suffix). If the recursive call for suffix returns true, we return true; otherwise, we try the next prefix. If we have tried all prefixes and none of them resulted in a solution, we return false.

```cpp
// C++ program to implement word break.
#include <bits/stdc++.h>
using namespace std;

// Function to check if the given string can be broken
// down into words from the word list
bool wordBreakRec(int i, string &s, vector<string> &dictionary)
{
    // If end of string is reached,
    // return true.
    if (i == s.length())
        return true;

    int n = s.length();
    string prefix = "";

    // Try every prefix
    for (int j = i; j < n; j++)
    {
        prefix += s[j];

        // if the prefix s[i..j] is a dictionary word
        // and rest of the string can also be broken into
        // valid words, return true
        if (find(dictionary.begin(), dictionary.end(), prefix) != dictionary.end() &&
            wordBreakRec(j + 1, s, dictionary))
        {
            return true;
        }
    }

    return false;
}

bool wordBreak(string &s, vector<string> &dictionary)
{
    return wordBreakRec(0, s, dictionary);
}

int main()
{
    string s = "ilike";
    vector<string> dictionary = {"i", "like", "gfg"};

    cout << (wordBreak(s, dictionary) ? "true" : "false") << endl;
    return 0;
}
```

### 
**Output**
```
true
```

### **[Expected Approach - 1] Using Top-Down DP - O(n^2) Time and O(n+m) Space**

> The idea is to use dynamic programming in the recursive solution to avoid recomputing the same subproblems. To further improve the time complexity, store the words of the dictionary in a set to improve the time complexity of looking for a word in the dictionary from O(m) to O(1).

### **[Expected Approach - 2] Using Bottom Up DP - O(n*m*k) time and O(n) space**

> The idea is to use bottom-up dynamic programming to determine if a string can be segmented into dictionary words. Create a boolean array dp[] where each position dp[i] represents whether the substring from 0 to that position can be broken into dictionary words.

```cpp
// C++ program to implement word break.
#include <bits/stdc++.h>
using namespace std;

bool wordBreak(string &s, vector<string> &dictionary)
{
    int n = s.size();
    vector<bool> dp(n + 1, 0);
    dp[0] = 1;

    // Traverse through the given string
    for (int i = 1; i <= n; i++)
    {
        // Traverse through the dictionary words
        for (string &w : dictionary)
        {
            // Check if current word is present
            // the prefix before the word is also
            // breakable
            int start = i - w.size();
            if (start >= 0 && dp[start] && s.substr(start, w.size()) == w)
            {
                dp[i] = 1;
                break;
            }
        }
    }
    return dp[n];
}

int main()
{
    string s = "ilike";
    vector<string> dictionary = {"i", "like", "gfg"};

    cout << (wordBreak(s, dictionary) ? "true" : "false") << endl;

    return 0;
}
```

**Time Complexity: O(n \* m \* k),** where n is the length of the string and m is the number of dictionary words and k is the length of the maximum sized string in the dictionary.
