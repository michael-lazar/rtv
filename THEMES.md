# Themes

Different themes can be used to customize the look and feel of RTV.
They control the color and special attributes (bold, underline, etc.) of
every text element drawn on the screen.

## Usage

Use the ``--theme`` flag to select a theme:

```bash
$ rtv --theme=papercolor
```

You can also view a list of built-in and installed themes by using the ``--list-themes`` flag:

```bash
$ rtv --list-themes

Installed (~/.config/rtv/themes/):
    (empty)

Presets:
    molokai             [requires 256 colors]
    papercolor          [requires 256 colors]
    solarized-dark      [requires 256 colors]
    solarized-light     [requires 256 colors]

Built-in:
    default             [requires 8 colors]
    monochrome          [requires 0 colors]
```

Custom themes can be installed by copying them into the **{HOME}/.config/rtv/themes/** folder.

RTV allows you to cycle through themes using the <kbd>F2</kbd> & <kbd>F3</kbd> keys.
This can be used to quickly preview the different options.

## Preview

<table>
  <tr>
    <td align="center">
      <strong>Default</strong>
      <p>This theme is designed to work with the terminal's preset 16 color palette</p>
      <img src="https://github.com/michael-lazar/rtv/blob/themes/resources/theme_default.png"></img>
    </td>
    <td align="center">
      <strong>Monochrome</strong>
      <p>This theme is a fallback for terminals that don't support colors</p>
      <img src="https://github.com/michael-lazar/rtv/blob/themes/resources/theme_solarized_light.png"></img>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Solarized Dark</strong>
      <img src="https://github.com/michael-lazar/rtv/blob/themes/resources/theme_solarized_dark.png"></img>
    </td>
    <td align="center">
      <strong>Solarized Light</strong>
      <img src="https://github.com/michael-lazar/rtv/blob/themes/resources/theme_solarized_light.png"></img>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>Papercolor</strong>
      <img src="https://github.com/michael-lazar/rtv/blob/themes/resources/theme_papercolor.png"></img>
    </td>
    <td align="center">
      <strong>Molokai</strong>
      <img src="https://github.com/michael-lazar/rtv/blob/themes/resources/theme_molokai.png"></img>
    </td>
  </tr>
</table>

## Designing a theme

```
[theme]
;<element>            = <foreground>  <background>  <attributes>
Normal                = default       default       -
Selected              = -             -             -
SelectedCursor        = -             -             reverse

TitleBar              = cyan          -             bold+reverse
OrderBar              = yellow        -             bold
OrderBarHighlight     = yellow        -             bold+reverse
HelpBar               = cyan          -             bold+reverse
Prompt                = cyan          -             bold+reverse
NoticeInfo            = -             -             bold
NoticeLoading         = -             -             bold
NoticeError           = -             -             bold
NoticeSuccess         = -             -             bold

CursorBlock           = -             -             -
CursorBar1            = magenta       -             -
CursorBar2            = cyan          -             -
CursorBar3            = green         -             -
CursorBar4            = yellow        -             -

CommentAuthor         = blue          -             bold
CommentAuthorSelf     = green         -             bold
CommentCount          = -             -             -
CommentText           = -             -             -
Created               = -             -             -
Downvote              = red           -             bold
Gold                  = yellow        -             bold
HiddenCommentExpand   = -             -             bold
HiddenCommentText     = -             -             -
MultiredditName       = yellow        -             bold
MultiredditText       = -             -             -
NeutralVote           = -             -             bold
NSFW                  = red           -             bold+reverse
Saved                 = green         -             -
Score                 = -             -             -
Separator             = -             -             bold
Stickied              = green         -             -
SubscriptionName      = yellow        -             bold
SubscriptionText      = -             -             -
SubmissionAuthor      = green         -             bold
SubmissionFlair       = red           -             -
SubmissionSubreddit   = yellow        -             -
SubmissionText        = -             -             -
SubmissionTitle       = -             -             bold
Upvote                = green         -             bold
Link                  = blue          -             underline
LinkSeen              = magenta       -             underline
UserFlair             = yellow        -             bold
```
