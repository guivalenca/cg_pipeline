---
id: "6"
title: "Conversão entre Bases"
source_url: "https://www.geeksforgeeks.org/bcd-or-binary-coded-decimal/"
fetch_url: "https://www.geeksforgeeks.org/bcd-or-binary-coded-decimal"
resolved_url: "https://www.geeksforgeeks.org/dsa/bcd-or-binary-coded-decimal/"
firecrawl_title: "BCD or Binary Coded Decimal - GeeksforGeeks"
description: "Your All-in-One Learning Portal: GeeksforGeeks is a comprehensive educational platform that empowers learners across domains-spanning computer science and programming, school education, upskilling, commerce, software tools, competitive exams, and more., Your All-in-One Learning Portal. It contains well written, well thought and well explained computer science and programming articles, quizzes and practice/competitive programming/company interview Questions."
fetched_at: "2026-05-12T03:59:50.992191Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "d855f724d066a4babcf1fcac0824afbdbb1a8a2033fb224d16187a2eeea40e02"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 1085
char_count: 6979
content_sha256: "a76df18fe2c7fd93e7f32bc39416320d3c162f85635ef17305525c96a2c8f695"
image_count: 4
link_count: 47
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "template_heavy_preserve_code_blocks"
---

# BCD or Binary Coded Decimal

Last Updated : 15 Jul, 2025

Binary Coded Decimal (BCD) is a binary encoding system in which each decimal digit is represented by a fixed number of binary bits, typically four. Instead of converting the entire decimal number into a binary number, BCD represents each decimal digit separately as its binary equivalent.

- BCD powers digital systems like clocks and calculators, making decimal displays possible.
- It’s the go-to choice for systems with human interaction, like digital displays and data entry tools.
- BCD makes arithmetic easier by treating each decimal digit separately.
- Embedded systems rely on BCD for fast and efficient decimal operations.

## **Working of Binary Coded Decimal**

In BCD, each decimal digit (0-9) is converted into its 4-bit binary equivalent. For example:

- Decimal 0 is represented as `0000` in BCD.
- Decimal 1 is represented as `0001` in BCD.
- Decimal 2 is represented as `0010` in BCD and so on.

For instance, the decimal number 57 would be represented in BCD as two separate 4-bit binary numbers:

- Decimal 5 becomes `0101`
- Decimal 7 becomes `0111`

So, 57 in BCD is represented as `0101 0111`.

## **Truth Table for Binary Coded Decimal**

| Decimal Number | BCD |
| --- | --- |
| 0 | 0000 |
| 1 | 0001 |
| 2 | 0010 |
| 3 | 0011 |
| 4 | 0100 |
| 5 | 0101 |
| 6 | 0110 |
| 7 | 0111 |
| 8 | 1000 |
| 9 | 1001 |

## BCD Representation Techniques

### 1. Packed BCD

Packed BCD is a type of Binary Coded Decimal where two decimal digits are stored in one byte (8 bits). In Packed BCD, each 4-bit nibble of a byte represents one decimal digit. Packed BCD saves memory space compared to other methods, as it uses one byte to store two digits, making it efficient for storage and processing in digital systems.

**Example:** Consider the decimal number 93. In Packed BCD, it is represented as 10010011:

- The first nibble (1001) represents 9.
- The second nibble (0011) represents 3.

### 2. Unpacked BCD

Unpacked BCD stores each decimal digit in a separate byte. Each byte contains one decimal digit, with the 4-bit nibble representing the decimal digit and the other 4 bits are unused or set to 0. Unpacked BCD uses more memory compared to Packed BCD, as each digit requires one full byte. However, it is simpler to work with in certain systems where each decimal digit needs to be accessed separately.

**Example:** For the decimal number 93, in Unpacked BCD:

- The first byte is 00001001 (representing 9).
- The second byte is 00000011 (representing 3).

## Common Operations on BCD Numbers

Common Operations on BCD Numbers involve basic arithmetic operations like addition, subtraction, multiplication, and division, with specific rules for handling BCD numbers.

### 1. BCD Addition

To add two BCD numbers, the sum of each corresponding digit is calculated. If the result exceeds 9 (1001 in binary), a correction factor of 6 (0110 in binary) is added to adjust the result.

**Example:** Adding decimal numbers 45 and 37 in BCD

Convert to BCD:

- 45 → 0100 0101
- 37 → 0011 0111

> 0100 0101 (45)
>  
> + 0011 0111 (37)
>  
> ---------
>  
> 0111 1100 (7 12)

This is an invalid BCD result as 12 (1100) is greater than 9 (1001) and sum should be equal to 82. For adjustment we add 6 (0110) to the result:

> 0111 1100 (Invalid result)
>  
> + 0000 0110 (Add correction factor)
>  
> 
> 
> 1000 0010 (82)

**Final BCD result:** 1000 0010, which represents the decimal value 82 in BCD.

### 2. BCD Subtraction

To subtract BCD numbers, similar to addition, borrow adjustments are made when the subtracted digit is greater than the minuend digit. A correction factor of 6 is added when needed.

**Example:** Subtracting decimal numbers 23 from 47 in BCD

Convert to BCD:

- 47 → 0100 0111
- 23 → 0010 0011

> 0100 0111 (47)
>  
> - 0010 0011 (23)
>  
> -----------
>  
> 0010 0100 (24) -> Valid BCD result

**Final BCD result:** 0010 0100, which represents the decimal value 24.

### 3. BCD Multiplication

Multiplying BCD numbers requires converting the BCD digits to their binary equivalents, performing the multiplication, and then converting the result back to BCD.

**Example:** Multiplying decimal numbers 5 by 3 in BCD

Convert to BCD:

- 5 → 0101
- 3 → 0011
- 5 x 3 = 15 → 0000 1111
- Convert binary result to BCD: 15 in binary → 0001 0101 in BCD

> 0101 (5 in binary)
>  
> x 0011 (3 in binary)
>  
> ---------
>  
> 0000 1111 (15 in binary)
>  
> 1 → 0001
>  
> 5 → 0101
>  
> 15 in BCD form: 0001 0101

**Final BCD result:** 0001 0101, which represents the decimal value 15.

### 4. BCD Division

Division follows the same principles as multiplication. The BCD numbers are first converted to binary, divided, and then the quotient is converted back to BCD.

**Example:** Dividing decimal number 18 by 3 in BCD

Convert to BCD:

- 18 → 0001 1000
- 3 → 0011
- 18 ÷ 3 = 6 → 0000 0110

> 0001 1000 (18 in binary)
>  
> ÷ 0011 (3 in binary)
>  
> -----------
>  
> 0000 0110 (6 in binary)

Convert binary result to BCD: 6 in binary → 0110 in BCD

**Final BCD result:** 0110, which represents the decimal value 6.

## Limitations of BCD

**1. Inefficient Use of Memory**: BCD uses more memory than pure binary representation. Each decimal digit is represented by 4 bits, leading to higher memory consumption compared to binary.

**2. Complex Arithmetic Operations**: Performing arithmetic operations like addition and multiplication is more complex in BCD. Extra correction factors are required when the result exceeds 9, making the process slower.

**3. Slower Processing Speed:** Due to the need for additional correction and conversion steps, BCD operations take longer than binary operations, affecting processing speed.

**4. Limited Range:** BCD can represent only decimal digits (0-9). It cannot handle fractional values efficiently without additional complexity, limiting its versatility in certain applications.

**5. Hardware Overhead**: Specialized hardware is required to handle BCD operations, which adds to the overall cost and complexity of digital systems.

## Applications of BCD

**1. Digital Displays**: BCD is used in devices like digital clocks and calculators to show decimal numbers as binary values, making it easier to display numbers on screens.

**2. Embedded Systems**: In embedded systems, BCD is ideal for processing or displaying decimal values, such as in financial applications, counters, and digital instruments.

**3. Data Conversion:** When decimal numbers need to be converted to binary or vice versa, BCD simplifies the process, which is useful in barcode scanners and other input devices.

**4. Arithmetic Operations:** BCD is crucial in systems that perform decimal-based arithmetic, as it allows easier and more accurate handling of decimal digits in addition, subtraction, and multiplication.

**5. Control Systems**: BCD plays a key role in control systems where decimal input and output are needed for precise decision-making and data processing.
