"""Simple Telegram bot that could help to manage a todo list."""

import config
import mysql.connector
import telebot
from telebot import types

bot = telebot.TeleBot(config.TOKEN)
db = mysql.connector.connect(host='localhost',
                             user=config.USER,
                             password=config.PASSWORD,
                             database='gettingthingsdone')
cursor = db.cursor()

markup = types.ReplyKeyboardMarkup()
markup.row('/todo', '/print_todo', '/print_done')
markup.row('/done', '/stats', '/help')

oops_message = 'Ooops! Something went wrong!' + '\U0001F630' * 3


@bot.message_handler(commands=["start"])
def start(message):
    """Send a welcoming message"""
    welcome_message= "Nice to meet you, <b>"+\
                     message.from_user.first_name+'</b>'+\
                     u'\U0001F61C'*2
    bot.send_message(message.chat.id,
                     welcome_message,
                     parse_mode='HTML',
                     reply_markup=markup)


@bot.message_handler(commands=["help"])
def help_message(message):
    """Show possible commands"""
    bot.send_message(message.chat.id, '<b>'+message.from_user.first_name+\
                     '</b>, try one of the following commands:\n'+\
                     "/todo - to add a new item in your todo list\n"+\
                     "/done - check the item you have done\n"+\
                     "/print_todo - to see your todo list\n"+\
                     "/print_done - to see your done list\n"+\
                     "/stats - to see your statistics\n"+\
                     "/stop - to delete all your information",\
                     reply_markup=markup)


@bot.message_handler(commands=["todo"])
def todo(message):
    """Add a new task to the Todo table, send an encouraging message."""
    try:
        task = message.text.replace('/todo', '').strip().capitalize()
        if not task:
            raise Exception
        sql = 'INSERT INTO ToDo (chat_id, task) VALUES (%s, %s)'
        values = (message.chat.id, task)
        cursor.execute(sql, values)
        db.commit()

        encouraging_message = '<b>'+message.from_user.first_name+\
                        '</b>, good luck with:'+'\n<i>'+\
                        task+'!!!</i>\n'+u'\U0001F4AA'*3
        bot.send_message(message.chat.id,
                         encouraging_message,
                         parse_mode='HTML',
                         reply_markup=markup)
    except:
        bot.send_message(message.chat.id,
                         oops_message,
                         parse_mode='HTML',
                         reply_markup=markup)


@bot.message_handler(commands=['done'])
def done_handler(message):
    """Create reply keyboard for user to choose task that they want to mark as done"""
    try:
        all_tasks = select_from_table('todo', 'task', message.chat.id)
        if not all_tasks:
            no_tasks_message = '<b>'+message.from_user.first_name+',</b> you should first add a task'+\
                'using a \\todo command!'
            bot.send_message(message.chat.id,
                             no_tasks_message,
                             parse_mode='HTML',
                             reply_markup=markup)
            return

        markup_with_tasks = types.InlineKeyboardMarkup()
        for task in all_tasks:
            button = types.InlineKeyboardButton(text=task,
                                                callback_data='/done_task ' +
                                                task)
            markup_with_tasks.add(button)
        choice_message = '<b>'+message.from_user.first_name+',</b>'+\
            ' select the task you have accomplished:'
        bot.send_message(message.chat.id,
                         choice_message,
                         parse_mode='HTML',
                         reply_markup=markup_with_tasks)
    except:
        bot.send_message(message.chat.id,
                         oops_message,
                         parse_mode='HTML',
                         reply_markup=markup)


@bot.callback_query_handler(lambda query: '/done_task' in query.data)
def answer_done_task_query(query):
    """Delete task from Todo table, add it to Done table, send a reply"""
    original_message = query.message
    task = query.data.replace('/done_task ', '')
    congrats_message =  'Congrats, <b>'+\
                 query.from_user.first_name+'</b>!!!'+u'\U0001F451'*3+\
                 "\nYou have accomplished a great thing:\n"+ "<i>"+\
                 task+'</i>!!! '+u'\U0001F44F'*3
    bot.answer_callback_query(query.id)
    try:
        sql = 'DELETE FROM ToDo WHERE chat_id=%s AND task =%s'
        values = (original_message.chat.id, task)
        cursor.execute(sql, values)
        sql = 'INSERT INTO done (chat_id, task) VALUES (%s,%s)'
        cursor.execute(sql, values)
        db.commit()
        bot.send_message(original_message.chat.id,
                         congrats_message,
                         parse_mode='HTML',
                         reply_markup=markup)
    except:
        bot.send_message(original_message.chat.id,
                         oops_message,
                         reply_markup=markup)


@bot.message_handler(commands=["print_todo"])
def print_todo_handler(message):
    """Print tasks from todo table"""
    all_tasks = ('\n' + u'\U0001F4CC').join(
        select_from_table('todo', 'task', message.chat.id))
    result_message = '<b>To-do:</b>' + '\n' + u'\U0001F4CC' + all_tasks
    bot.send_message(message.chat.id,
                     result_message,
                     parse_mode='HTML',
                     reply_markup=markup)


@bot.message_handler(commands=["print_done"])
def print_done_handler(message):
    """Print tasks from done table"""
    all_tasks = ('\n' + u'\U00002705').join(
        select_from_table('done', 'task', message.chat.id))
    result_message = '<b>Done:</b>' + '\n' + u'\U00002705' + all_tasks
    bot.send_message(message.chat.id,
                     result_message,
                     parse_mode='HTML',
                     reply_markup=markup)


@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show # of tasks in todo and done tables"""
    todo_tasks = select_from_table('todo', 'task', message.chat.id)
    done_tasks = select_from_table('done', 'task', message.chat.id)
    stats_message='<b>'+message.from_user.first_name+'</b>, here is your statistics:\n'+\
        'You have done <b>{}</b> tasks! '.format(len(done_tasks),)+\
            'You have to do <b>{}</b> tasks!'.format(len(todo_tasks),)+\
                'Keep going!'+'\U0000270A'*3
    bot.send_message(message.chat.id,
                     stats_message,
                     parse_mode='HTML',
                     reply_markup=markup)


@bot.message_handler(commands=['stop'])
def stop(message):
    """Erase all data from the user and say Goodbye"""
    delete_from_table('todo', message.chat.id)
    delete_from_table('done', message.chat.id)
    bye_message = 'Goodbye, <b>'+\
                 message.from_user.first_name+'</b>! '+'All you data was deleted!\n'+\
                 'It\'s a pity to see you go(('+ '\U0001F630'*3
    bot.send_message(message.chat.id,
                     bye_message,
                     parse_mode='HTML',
                     reply_markup=markup)


def select_from_table(table_name, col_name, chat_id):
    """Select values from given column in given table"""
    sql = 'SELECT DISTINCT {} FROM {} WHERE chat_id=%s'.format(
        col_name, table_name)
    values = (chat_id, )
    cursor.execute(sql, values)
    all_records = [record[0] for record in cursor.fetchall()]
    return all_records


def delete_from_table(table_name, chat_id):
    """Delete all records in table from given chat"""
    sql = 'DELETE FROM {} WHERE chat_id={}'.format(table_name, chat_id)
    cursor.execute(sql)
    db.commit()


if __name__ == "__main__":
    bot.polling()
