Feature: Video component
  As a student, I want to view course videos in LMS.

  Scenario: Autoplay is enabled in LMS for a Video component
  Given the course has a Video component
  Then when I view the video it has autoplay enabled
