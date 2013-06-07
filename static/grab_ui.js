/* Author: 

*/

OPEN  = '&#x25BC;';
OPENED  = '\u25BC';
CLOSE = '&#x25BA;';
WARNING = '<font color="red" size="5">&#x26a0;</font>';
CHECKMARK = '&#x2713;&nbsp;';

LOADING = 'loading...';

var clickmap = {};

COLORCYCLE = 16;
var colorindex = 0;
var colormap = {};

function getURLParameter(name) {
  return decodeURI(
    (RegExp(name + '=' + '(.+?)(&|$)').exec(location.search)||[,null])[1]
  );
}

function quote(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function get_json(url, success_callback, error_callback) {
  $.ajax({ url: url,
           cache: false,
           dataType: 'json',
           error: error_callback,
           success: success_callback });
}

function click_to_open(tag, renderer) {
  var id = tag.attr('id');
  var id_stem = id.replace('tag_', '');
  var body = $('#body_'+id_stem);
  if (tag.html() === OPENED) {
    tag.html(CLOSE);
    body.hide();
  } else {
    tag.html(OPEN);
    body.show();
    if (!body.html()) {
      if (id_stem in clickmap) {
        body.html(LOADING);
        var entry = clickmap[id_stem];
        entry.renderer(body, id_stem, entry.data, entry.base, entry.aux);
      } else {
        body.html('<em>No clickmap entry for: '+id_stem+'</em>');
      }
    }
  }
}

function text_to_open(tag) {
  var id = tag.attr('id');
  var id_stem = id.replace('text_', '');
  var body = $('#body_'+id_stem);
  $('#tag_'+id_stem).html(OPEN);
  body.html('<ul><li><em>Searching...</em></li></ul>');
  body.show();
  if (id_stem in clickmap) {
    body.html(LOADING);
    var entry = clickmap[id_stem];
    entry.renderer(body, id_stem, entry.data, entry.base);
  } else {
    body.html('<em>No clickmap entry for: '+id_stem+'</em>');
  }
}

function check_to_open(tag) {
  var parent = tag.parent().parent().parent();
  var grandparent = parent.children('div.body').children('ul');
  var checkboxes = grandparent.children('li').children('ul').children('li').children('span').children('nobr').children('.commit_checkbox');
  var hiddenrows = grandparent.children('li.hiddenrow');
  var checked = tag.attr('checked');
  if (checkboxes.size() > 0) {
    grandparent.children('.commit_checkbox').hide();
    checkboxes.each(function() {
        var classname = $(this).attr('class').replace('commit_checkbox ','');
        if ($(this).attr('checked')) grandparent.children('li.'+classname).show();
      });
  } else if (checked) hiddenrows.show();
  if (!checked) hiddenrows.hide();
  var opener = parent.children('.tag');
  if (opener.html() !== OPENED) opener.click();
}

function process_array(items, process, callback) {
  if (items.length > 0) {
    var todo = items.concat();
    setTimeout(function() {
      var start = +new Date();
      do {
        process(todo.shift());
      } while (todo.length > 0 && (+new Date() - start < 50));
      if (todo.length > 0) {
        setTimeout(arguments.callee, 25);
      } else {
        callback();
      }
    }, 25);
  } else callback();
}

function render_dot(color) {
  if (color in colormap) return '<span class="bullet_'+(colormap[color])+'">&#x25CF;</span>';
  return '';
}

function decorate_click_and_hide(body, html_table, html_ul)
{
  var html = "";
  if (html_table) html += '<li><table>'+html_table+'</table></li>';
  html += html_ul;
  if (html) {
    var parent_checkbox = body.parent().find(".checkbox");
    body.html('<ul>'+html+'</ul>');
    body.find('.body').hide();
    if (parent_checkbox.length > 0) {
      if (parent_checkbox.attr('checked')) {
        body.find('.hiddenrow').show();
      } else {
        body.find('.hiddenrow').hide();
      }
    }
    body.find('.text').change(function () { text_to_open($(this)); });
    body.find('.tag').click(function () { click_to_open($(this)); });
    body.find('.checkbox').click(function () { check_to_open($(this)); });
    body.find('.commit_checkbox').click(function () { check_to_open_commit($(this)); });
  } else {
    body.html("<em>No Data</em>");
  }
}

function render_plural(n, word, s)
{
  if (typeof s === 'undefined') s = 's';
  return (n===0?'no':(n===1?'one':n))+' '+word+(n===1?'':s);
}

function render_expandable(hidden, id, state, head, renderer, data, base, aux, other_classes)
{
  if (id in clickmap) console.log("duplicate id: "+id+"; head="+head);
  clickmap[id] = { "renderer": renderer, "data": data, "base": base, "aux": aux };
  var classes = "";
  if (hidden) classes += 'hiddenrow';
  var dots="";
  if (other_classes) {
    classes += ' commit_checkbox';
    for (var i=0; i<other_classes.length; i++) {
      dots += render_dot(other_classes[i]);
      classes += ' commit_checkbox_'+base.serial+'_'+other_classes[i];
    }
  }
  return '<li class="'+classes+'">'+
         '<span class="tag" id="tag_'+id+'">'+state+'</span>'+
         '<span class="head"><nobr>'+dots+head+'</nobr></span>'+
         '<div class="body" id="body_'+id+'"></div></li>';
}

$(document).ready(function () {
  $('ul.tabs').each(function(){
    // For each set of tabs, we want to keep track of
    // which tab is active and it's associated content
    var $active, $content, $links = $(this).find('a');

    // If the location.hash matches one of the links, use that as the active tab.
    // If no match is found, use the first link as the initial active tab.
    $active = $($links.filter('[href="'+location.hash+'"]')[0] || $links[0]);
    $active.addClass('active');
    $content = $($active.attr('href'));

    // Hide the remaining content
    $links.not($active).each(function () {
      $($(this).attr('href')).hide();
    });

    // Bind the click event handler
    $(this).on('click', 'a', function(e){
      // Make the old tab inactive.
      $active.removeClass('active');
      $content.hide();

      // Update the variables with the new link and content
      $active = $(this);
      $content = $($(this).attr('href'));

      // Make the tab active.
      $active.addClass('active');
      $content.show();

      // Prevent the anchor's default click action
      e.preventDefault();
    });
  });

  get_json("/?op=dump",
    function (json) {
      if (json) {
        // Set grab lock version
        $('#version').html(json.data.config.version);
      }
    },
    function (jqXHR, textStatus, errorThrown) {
      console.log(textStatus, errorThrown);
    });
});
