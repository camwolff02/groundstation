set number 					" enable line numbers for current line
set relativenumber			" enable relative line number for other lines
set tabstop=4				" set tabs explicitly to 4 spaces
set shiftwidth=4			" same with shifts
set smarttab				" use spaces instead of tabs
"noremap <Up> <Nop>			" unbind arrow key for preventing bad habits
"noremap <Down> <Nop>		" unbind arrow key for preventing bad habits
"noremap <Left> <Nop>		" unbind arrow key for preventing bad habits
"noremap <Right> <Nop>		" unbind arrow key for preventing bad habits
colorscheme slate			" set colorscheme to ron or zaibatsu (mac)
syntax on					" enable syntax hilighting
set so=15					" set page to only start scrolling at +- 15 lines
set cursorline				" Highlight the horizontal line the cursor is on
set colorcolumn=80 			" Show 80 character with vertical line
set autoindent				" Automatically indent on tab
set smartindent				" Intelligently detect how much to indent
set wildmenu				" Enables tab autocomplete
set wildmode=list:longest	" Makes wildmenue behave like bash completion
